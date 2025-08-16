import importlib
import os
import sys
from unittest.mock import patch, Mock

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _load_admin_routes():
    from functools import wraps

    def fake_require_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import g
            g.current_admin = {"admin_id": 1, "role": "admin"}
            g.auth_service = Mock()
            return f(*args, **kwargs)
        return wrapper

    def fake_require_permission(_):
        def decorator(f):
            return f
        return decorator

    with patch("api.middleware.jwt_middleware.JWTMiddleware.require_auth", fake_require_auth), \
         patch("api.middleware.jwt_middleware.JWTMiddleware.require_permission", fake_require_permission):
        return importlib.reload(importlib.import_module("api.routes.admin_routes"))


def _create_app(module):
    app = Flask(__name__)
    app.register_blueprint(module.admin_bp, url_prefix="/api/admins")
    return app


def test_get_all_admins_calls_service():
    admin_routes = _load_admin_routes()
    app = _create_app(admin_routes)
    client = app.test_client()

    with patch.object(admin_routes, "get_admin_service") as mock_service:
        service = mock_service.return_value
        service.get_all_admins.return_value = [
            {"id": 1, "username": "a"}
        ]
        response = client.get("/api/admins/")
        assert response.status_code == 200
        service.get_all_admins.assert_called_once_with(1)


def test_create_admin_missing_fields():
    admin_routes = _load_admin_routes()
    app = _create_app(admin_routes)
    client = app.test_client()

    response = client.post("/api/admins/", json={"username": "a"})
    assert response.status_code == 400
