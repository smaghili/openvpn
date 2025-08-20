import importlib
import os
import sys
from unittest.mock import patch, Mock

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _create_app(module):
    app = Flask(__name__)
    app.register_blueprint(module.auth_bp, url_prefix="/api/auth")
    return app


def test_login_success():
    auth_routes = importlib.import_module("api.routes.auth_routes")
    app = _create_app(auth_routes)
    client = app.test_client()

    with patch.object(auth_routes, "get_auth_service") as mock_service:
        service = mock_service.return_value
        service.login.return_value = {"token": "abc"}
        response = client.post("/api/auth/login", json={"username": "u", "password": "p"})
        assert response.status_code == 200
        service.login.assert_called_once()


def test_login_missing_credentials():
    auth_routes = importlib.import_module("api.routes.auth_routes")
    app = _create_app(auth_routes)
    client = app.test_client()

    response = client.post("/api/auth/login", json={"username": "u"})
    assert response.status_code == 400


def _load_auth_routes_for_logout(mock_service):
    from functools import wraps

    def fake_require_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import g
            g.auth_service = mock_service
            g.current_admin = {"admin_id": 1, "role": "admin"}
            return f(*args, **kwargs)
        return wrapper

    with patch("api.middleware.jwt_middleware.JWTMiddleware.require_auth", fake_require_auth):
        module = importlib.reload(importlib.import_module("api.routes.auth_routes"))
    module.JWTMiddleware._extract_token = lambda _request: "tok"
    return module


def test_logout_calls_service():
    mock_service = Mock()
    auth_routes = _load_auth_routes_for_logout(mock_service)
    app = _create_app(auth_routes)
    client = app.test_client()

    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    mock_service.logout.assert_called_once_with("tok")
