import os
import sys
from unittest.mock import MagicMock

import bcrypt
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.admin_repository import AdminRepository
from core.exceptions import DatabaseError
from data.db import Database


def test_verify_password_success():
    db = MagicMock(spec=Database)
    repo = AdminRepository(db)
    password = "secret"
    hashpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    repo.get_admin_by_username = MagicMock(return_value={"password_hash": hashpw, "id": 1})
    admin = repo.verify_password("user", password)
    assert admin["id"] == 1


def test_verify_password_wrong_password():
    db = MagicMock(spec=Database)
    repo = AdminRepository(db)
    hashpw = bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode()
    repo.get_admin_by_username = MagicMock(return_value={"password_hash": hashpw})
    assert repo.verify_password("user", "wrong") is None


def test_verify_password_invalid_hash_raises():
    db = MagicMock(spec=Database)
    repo = AdminRepository(db)
    repo.get_admin_by_username = MagicMock(return_value={"password_hash": None})
    with pytest.raises(DatabaseError):
        repo.verify_password("user", "pw")
