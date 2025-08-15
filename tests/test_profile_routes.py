import importlib
import os
import sys
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _load_profile_routes():
    """Import profile_routes with authentication decorators patched."""

    from functools import wraps

    def fake_require_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import g
            g.current_admin = {"admin_id": 1, "role": "admin"}
            return f(*args, **kwargs)

        return wrapper

    def fake_require_permission(_):
        def decorator(f):
            return f

        return decorator

    with patch(
        "api.middleware.jwt_middleware.JWTMiddleware.require_auth",
        fake_require_auth,
    ), patch(
        "api.middleware.jwt_middleware.JWTMiddleware.require_permission",
        fake_require_permission,
    ):
        import types

        dummy_img = type("Img", (), {"save": lambda self, buf, format=None: None})
        dummy_qr = type(
            "QR",
            (),
            {
                "add_data": lambda self, data: None,
                "make": lambda self, fit=True: None,
                "make_image": lambda self, **k: dummy_img(),
            },
        )
        sys.modules.setdefault(
            "qrcode", types.SimpleNamespace(QRCode=lambda *a, **k: dummy_qr())
        )
        module = importlib.reload(importlib.import_module("api.routes.profile_routes"))

    return module


def _create_test_app(profile_routes_module):
    app = Flask(__name__)
    app.register_blueprint(
        profile_routes_module.profile_bp, url_prefix="/api/profile"
    )
    return app


def test_get_profile_link_calls_get_user_by_id():
    profile_routes = _load_profile_routes()
    app = _create_test_app(profile_routes)
    client = app.test_client()

    with patch.object(profile_routes, "get_security_service"), patch.object(
        profile_routes, "Database"
    ), patch.object(profile_routes, "UserRepository") as mock_repo:
        repo_instance = mock_repo.return_value
        repo_instance.get_user_by_id.return_value = {
            "id": 1,
            "created_by": 1,
            "profile_token": "token",
        }

        response = client.get("/api/profile/users/1/profile-link")

        assert response.status_code == 200
        repo_instance.get_user_by_id.assert_called_once_with(1)


def test_get_profile_link_user_not_found():
    profile_routes = _load_profile_routes()
    app = _create_test_app(profile_routes)
    client = app.test_client()

    with patch.object(profile_routes, "get_security_service"), patch.object(
        profile_routes, "Database"
    ), patch.object(profile_routes, "UserRepository") as mock_repo:
        repo_instance = mock_repo.return_value
        repo_instance.get_user_by_id.return_value = None

        response = client.get("/api/profile/users/99/profile-link")

        assert response.status_code == 404
    repo_instance.get_user_by_id.assert_called_once_with(99)


def test_get_qr_code_returns_png():
    profile_routes = _load_profile_routes()
    app = _create_test_app(profile_routes)
    client = app.test_client()

    with patch.object(profile_routes, "check_ip_rate_limit", return_value=True), \
         patch.object(profile_routes, "get_security_service") as mock_service:
        service_instance = mock_service.return_value
        service_instance.validate_profile_access.return_value = {"username": "user"}

        response = client.get("/api/profile/token/qr-code")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/png"

