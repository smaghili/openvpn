import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.jwt_service import JWTService
from core.exceptions import AuthenticationError


@pytest.fixture
def jwt_service(monkeypatch):
    """Create JWTService with deterministic secret."""
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    return JWTService.create_service()


def test_generate_and_validate_token(jwt_service):
    token_data = jwt_service.generate_token(
        admin_id=1, username="alice", role="admin", token_version=1
    )

    payload = jwt_service.validate_token(token_data["token"])

    assert payload["admin_id"] == 1
    assert payload["username"] == "alice"
    assert payload["role"] == "admin"
    assert payload["token_version"] == 1
    assert payload["jti"] == token_data["token_id"]


def test_invalid_and_expired_tokens(jwt_service):
    # invalid token string
    with pytest.raises(AuthenticationError):
        jwt_service.validate_token("invalid.token")

    # expired token
    jwt_service.token_expiry_hours = -1
    expired_token = jwt_service.generate_token(1, "bob", "admin", 1)["token"]
    with pytest.raises(AuthenticationError):
        jwt_service.validate_token(expired_token)


def test_blacklisted_token_rejected(jwt_service):
    token_data = jwt_service.generate_token(1, "eve", "admin", 1)

    # token initially valid
    jwt_service.validate_token(token_data["token"])

    # blacklist the token
    jwt_service.blacklist_token(token_data["token_id"])

    with pytest.raises(AuthenticationError):
        jwt_service.validate_token(token_data["token"])
