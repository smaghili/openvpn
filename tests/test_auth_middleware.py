import os
from unittest.mock import patch
from flask import Flask, jsonify

from api.middleware.auth_middleware import AuthMiddleware


def create_app():
    app = Flask(__name__)
    with patch.dict(os.environ, {"OPENVPN_API_KEY": "testkey"}):
        AuthMiddleware.init_app(app)

    @app.route("/protected")
    @AuthMiddleware.require_auth
    def protected():
        return jsonify({"status": "ok"})

    return app


def test_missing_api_key():
    app = create_app()
    client = app.test_client()
    response = client.get("/protected")
    assert response.status_code == 401


def test_invalid_api_key():
    app = create_app()
    client = app.test_client()
    response = client.get("/protected", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_valid_api_key():
    app = create_app()
    client = app.test_client()
    response = client.get("/protected", headers={"X-API-Key": "testkey"})
    assert response.status_code == 200
