"""
Unit tests for UserService class.
Tests all user management operations with proper mocking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from service.user_service import UserService
from core.exceptions import UserNotFoundError, ValidationError, UserAlreadyExistsError
from core.types import Username, Password

class TestUserService:
    """Test cases for UserService class."""
    
    @pytest.fixture
    def mock_user_repo(self):
        """Create a mock user repository."""
        return Mock()
    
    @pytest.fixture
    def mock_openvpn_manager(self):
        """Create a mock OpenVPN manager."""
        return Mock()
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        cache_mock = Mock()
        cache_mock.get.return_value = None
        cache_mock.set.return_value = None
        cache_mock.delete.return_value = None
        cache_mock.invalidate_cache.return_value = None
        return cache_mock
    
    @pytest.fixture
    def user_service(self, mock_user_repo, mock_openvpn_manager, mock_cache_manager):
        """Create UserService instance with mocked dependencies."""
        with patch('service.user_service.get_cache_manager', return_value=mock_cache_manager):
            return UserService(mock_user_repo, mock_openvpn_manager)
    
    def test_create_user_success_with_password(self, user_service, mock_user_repo, mock_openvpn_manager):
        """Test successful user creation with password."""
        # Arrange
        username = "testuser"
        password = "testpass123"
        user_id = 1
        
        mock_user_repo.find_user_by_username.return_value = None
        mock_user_repo.create_user_in_db.return_value = user_id
        mock_user_repo.create_user_protocol.return_value = True
        
        # Act
        result = user_service.create_user(username, password)
        
        # Assert
        assert result["username"] == username
        assert result["user_id"] == user_id
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.create_user_in_db.assert_called_once_with(username)
        mock_user_repo.create_user_protocol.assert_called_once_with(user_id, "login", "password")
        mock_openvpn_manager.create_user_certificate.assert_not_called()
    
    def test_create_user_success_without_password(self, user_service, mock_user_repo, mock_openvpn_manager):
        """Test successful user creation without password (certificate-based)."""
        # Arrange
        username = "testuser"
        user_id = 1
        
        mock_user_repo.find_user_by_username.return_value = None
        mock_user_repo.create_user_in_db.return_value = user_id
        mock_user_repo.create_user_protocol.return_value = True
        
        # Act
        result = user_service.create_user(username)
        
        # Assert
        assert result["username"] == username
        assert result["user_id"] == user_id
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.create_user_in_db.assert_called_once_with(username)
        mock_user_repo.create_user_protocol.assert_called_once_with(user_id, "cert", "certificate")
        mock_openvpn_manager.create_user_certificate.assert_called_once_with(username)
    
    def test_create_user_validation_error_short_username(self, user_service):
        """Test user creation with invalid short username."""
        # Arrange
        username = "ab"  # Too short
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Username must be at least 3 characters long"):
            user_service.create_user(username)
    
    def test_create_user_validation_error_empty_username(self, user_service):
        """Test user creation with empty username."""
        # Arrange
        username = ""
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Username must be at least 3 characters long"):
            user_service.create_user(username)
    
    def test_create_user_already_exists(self, user_service, mock_user_repo):
        """Test user creation when user already exists."""
        # Arrange
        username = "existinguser"
        existing_user = {"id": 1, "username": username}
        
        mock_user_repo.find_user_by_username.return_value = existing_user
        
        # Act & Assert
        with pytest.raises(ValidationError, match=f"User '{username}' already exists"):
            user_service.create_user(username)
    
    def test_delete_user_success(self, user_service, mock_user_repo, mock_openvpn_manager):
        """Test successful user deletion."""
        # Arrange
        username = "testuser"
        user_data = {"id": 1, "username": username}
        
        mock_user_repo.find_user_by_username.return_value = user_data
        mock_user_repo.delete_user.return_value = True
        
        # Act
        result = user_service.delete_user(username)
        
        # Assert
        assert result["message"] == f"User '{username}' deleted successfully"
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.delete_user.assert_called_once_with(user_data["id"])
        mock_openvpn_manager.revoke_user_certificate.assert_called_once_with(username)
    
    def test_delete_user_not_found(self, user_service, mock_user_repo):
        """Test user deletion when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match=f"User '{username}' not found"):
            user_service.delete_user(username)
    
    def test_get_user_success(self, user_service, mock_user_repo):
        """Test successful user retrieval."""
        # Arrange
        username = "testuser"
        user_data = {"id": 1, "username": username, "status": "active"}
        
        mock_user_repo.find_user_by_username.return_value = user_data
        
        # Act
        result = user_service.get_user(username)
        
        # Assert
        assert result == user_data
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
    
    def test_get_user_not_found(self, user_service, mock_user_repo):
        """Test user retrieval when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act
        result = user_service.get_user(username)
        
        # Assert
        assert result is None
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
    
    def test_get_all_users_success(self, user_service, mock_user_repo):
        """Test successful retrieval of all users."""
        # Arrange
        users_data = [
            {"id": 1, "username": "user1", "status": "active"},
            {"id": 2, "username": "user2", "status": "inactive"}
        ]
        
        mock_user_repo.get_all_users.return_value = users_data
        
        # Act
        result = user_service.get_all_users()
        
        # Assert
        assert result == users_data
        mock_user_repo.get_all_users.assert_called_once()
    
    def test_get_active_users_success(self, user_service, mock_user_repo):
        """Test successful retrieval of active users."""
        # Arrange
        active_users = [
            {"id": 1, "username": "user1", "status": "active"},
            {"id": 3, "username": "user3", "status": "active"}
        ]
        
        mock_user_repo.get_active_users.return_value = active_users
        
        # Act
        result = user_service.get_active_users()
        
        # Assert
        assert result == active_users
        mock_user_repo.get_active_users.assert_called_once()
    
    def test_update_user_status_success(self, user_service, mock_user_repo):
        """Test successful user status update."""
        # Arrange
        username = "testuser"
        new_status = "inactive"
        user_data = {"id": 1, "username": username, "status": "active"}
        
        mock_user_repo.find_user_by_username.return_value = user_data
        mock_user_repo.update_user_status.return_value = True
        
        # Act
        result = user_service.update_user_status(username, new_status)
        
        # Assert
        assert result["message"] == f"User '{username}' status updated to '{new_status}'"
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.update_user_status.assert_called_once_with(username, new_status)
    
    def test_update_user_status_invalid_status(self, user_service):
        """Test user status update with invalid status."""
        # Arrange
        username = "testuser"
        invalid_status = "invalid_status"
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Status must be 'active' or 'inactive'"):
            user_service.update_user_status(username, invalid_status)
    
    def test_update_user_status_user_not_found(self, user_service, mock_user_repo):
        """Test user status update when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        status = "active"
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match=f"User '{username}' not found"):
            user_service.update_user_status(username, status)
    
    def test_get_user_quota_success(self, user_service, mock_user_repo):
        """Test successful user quota retrieval."""
        # Arrange
        username = "testuser"
        user_data = {"id": 1, "username": username}
        quota_data = {"quota_bytes": 1073741824, "bytes_used": 536870912}  # 1GB quota, 512MB used
        
        mock_user_repo.find_user_by_username.return_value = user_data
        mock_user_repo.get_user_quota.return_value = quota_data
        
        # Act
        result = user_service.get_user_quota(username)
        
        # Assert
        assert result == quota_data
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.get_user_quota.assert_called_once_with(user_data["id"])
    
    def test_get_user_quota_user_not_found(self, user_service, mock_user_repo):
        """Test user quota retrieval when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match=f"User '{username}' not found"):
            user_service.get_user_quota(username)
    
    def test_set_user_quota_success(self, user_service, mock_user_repo):
        """Test successful user quota setting."""
        # Arrange
        username = "testuser"
        quota_gb = 5
        user_data = {"id": 1, "username": username}
        
        mock_user_repo.find_user_by_username.return_value = user_data
        mock_user_repo.update_user_quota.return_value = True
        
        # Act
        result = user_service.set_user_quota(username, quota_gb)
        
        # Assert
        assert result["message"] == f"Quota for user '{username}' set to {quota_gb}GB"
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.update_user_quota.assert_called_once_with(user_data["id"], quota_gb * (1024**3))
    
    def test_set_user_quota_negative_value(self, user_service):
        """Test user quota setting with negative value."""
        # Arrange
        username = "testuser"
        negative_quota = -1
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Quota must be non-negative"):
            user_service.set_user_quota(username, negative_quota)
    
    def test_set_user_quota_user_not_found(self, user_service, mock_user_repo):
        """Test user quota setting when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        quota_gb = 5
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match=f"User '{username}' not found"):
            user_service.set_user_quota(username, quota_gb)
    
    def test_get_user_stats_success(self, user_service, mock_user_repo):
        """Test successful user statistics retrieval."""
        # Arrange
        username = "testuser"
        user_data = {"id": 1, "username": username, "status": "active", "created_at": "2024-01-01"}
        quota_info = {"quota_bytes": 1073741824, "bytes_used": 536870912}
        
        mock_user_repo.find_user_by_username.return_value = user_data
        mock_user_repo.get_user_quota_status.return_value = quota_info
        
        # Act
        result = user_service.get_user_stats(username)
        
        # Assert
        expected_result = {
            "username": username,
            "status": "active",
            "quota_bytes": quota_info["quota_bytes"],
            "bytes_used": quota_info["bytes_used"],
            "created_at": "2024-01-01"
        }
        assert result == expected_result
        
        mock_user_repo.find_user_by_username.assert_called_once_with(username)
        mock_user_repo.get_user_quota_status.assert_called_once_with(user_data["id"])
    
    def test_get_user_stats_user_not_found(self, user_service, mock_user_repo):
        """Test user statistics retrieval when user doesn't exist."""
        # Arrange
        username = "nonexistentuser"
        
        mock_user_repo.find_user_by_username.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError, match=f"User '{username}' not found"):
            user_service.get_user_stats(username)
    
    def test_get_system_stats_success(self, user_service, mock_user_repo):
        """Test successful system statistics retrieval."""
        # Arrange
        all_users = [{"id": 1}, {"id": 2}, {"id": 3}]
        active_users = [{"id": 1}, {"id": 2}]
        online_users_count = 1
        total_usage = 1073741824  # 1GB
        
        mock_user_repo.get_all_users.return_value = all_users
        mock_user_repo.get_active_users.return_value = active_users
        mock_user_repo.get_online_users_count.return_value = online_users_count
        mock_user_repo.get_total_usage.return_value = total_usage
        
        # Act
        result = user_service.get_system_stats()
        
        # Assert
        expected_result = {
            "total_users": 3,
            "active_users": 2,
            "online_users": 1,
            "total_usage_bytes": 1073741824
        }
        assert result == expected_result
        
        mock_user_repo.get_all_users.assert_called_once()
        mock_user_repo.get_active_users.assert_called_once()
        mock_user_repo.get_online_users_count.assert_called_once()
        mock_user_repo.get_total_usage.assert_called_once()
