import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from service.user_service import UserService


def _create_service():
    user_repo = Mock()
    openvpn_manager = Mock()
    login_manager = Mock()
    return UserService(user_repo, openvpn_manager, login_manager), user_repo, openvpn_manager, login_manager


def test_create_user_success():
    service, user_repo, openvpn_manager, login_manager = _create_service()
    user_repo.find_user_by_username.return_value = None
    user_repo.add_user.return_value = 1
    service._generate_user_certificate_config = Mock(return_value="config")

    result = service.create_user("alice", "pw")
    assert result == "config"
    user_repo.add_user.assert_called_once()
    login_manager.add_user.assert_called_once_with("alice", "pw")


def test_remove_user_calls_managers():
    service, user_repo, openvpn_manager, login_manager = _create_service()
    user_repo.find_user_by_username.return_value = {"id": 1}

    service.remove_user("bob")
    openvpn_manager.revoke_user_certificate.assert_called_once_with("bob")
    login_manager.remove_user.assert_called_once_with("bob")
    user_repo.remove_user.assert_called_once_with("bob")
