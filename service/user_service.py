from typing import Dict, Any, List, Optional
import bcrypt
import os
from data.user_repository import UserRepository
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import DATABASE_FILE
from core.backup_interface import IBackupable
from core.types import Username, Password, ConfigData, UserData
from config.shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
from core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    CertificateGenerationError,
    DatabaseError,
    ValidationError
)
from core.cache_manager import get_cache_manager
from core.logging_config import LoggerMixin, log_function_call, log_performance

class UserService(LoggerMixin):
    def __init__(self, user_repo: UserRepository, openvpn_manager: OpenVPNManager):
        self.user_repo = user_repo
        self.openvpn_manager = openvpn_manager
        self.cache_manager = get_cache_manager()
    @log_function_call
    @log_performance
    def create_user(self, username: Username, password: str = "") -> Dict[str, Any]:
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        existing_user = self.user_repo.find_user_by_username(username)
        if existing_user:
            raise ValidationError(f"User '{username}' already exists")
        user_id = self.user_repo.create_user_in_db(username)
        if password:
            self.user_repo.create_user_protocol(user_id, "login", "password")
            self.logger.info("User created with password authentication", username=username, user_id=user_id)
        else:
            self.openvpn_manager.create_user_certificate(username)
            self.user_repo.create_user_protocol(user_id, "cert", "certificate")
            self.logger.info("User created with certificate authentication", username=username, user_id=user_id)
        self.cache_manager.invalidate_cache("user_data")
        self.cache_manager.invalidate_cache("system_stats")
        return {"username": username, "user_id": user_id}
    def delete_user(self, username: Username) -> Dict[str, Any]:
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        self.user_repo.delete_user(user['id'])
        self.openvpn_manager.revoke_user_certificate(username)
        self.cache_manager.invalidate_cache("user_data")
        self.cache_manager.invalidate_cache("system_stats")
        return {"message": f"User '{username}' deleted successfully"}
    @get_cache_manager().cached("user_data", ttl=300)
    def get_user(self, username: Username) -> Optional[Dict[str, Any]]:
        return self.user_repo.find_user_by_username(username)
    @get_cache_manager().cached("user_data", ttl=300)
    def get_all_users(self) -> List[Dict[str, Any]]:
        return self.user_repo.get_all_users()
    @get_cache_manager().cached("user_data", ttl=120)
    def get_active_users(self) -> List[Dict[str, Any]]:
        return self.user_repo.get_active_users()
    def update_user_status(self, username: Username, status: str) -> Dict[str, Any]:
        if status not in ['active', 'inactive']:
            raise ValidationError("Status must be 'active' or 'inactive'")
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        success = self.user_repo.update_user_status(username, status)
        if not success:
            raise ValidationError(f"Failed to update user '{username}' status")
        self.cache_manager.invalidate_cache("user_data")
        return {"message": f"User '{username}' status updated to '{status}'"}
    @get_cache_manager().cached("quota_data", ttl=120)
    def get_user_quota(self, username: Username) -> Optional[Dict[str, Any]]:
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        return self.user_repo.get_user_quota(user['id'])
    def set_user_quota(self, username: Username, quota_gb: int) -> Dict[str, Any]:
        if quota_gb < 0:
            raise ValidationError("Quota must be non-negative")
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        quota_bytes = quota_gb * (1024 ** 3)
        success = self.user_repo.update_user_quota(user['id'], quota_bytes)
        if not success:
            raise ValidationError(f"Failed to update quota for user '{username}'")
        self.cache_manager.invalidate_cache("quota_data")
        return {"message": f"Quota for user '{username}' set to {quota_gb}GB"}
    @get_cache_manager().cached("user_data", ttl=120)
    def get_user_stats(self, username: Username) -> Dict[str, Any]:
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        quota_info = self.user_repo.get_user_quota_status(user['id'])
        return {
            "username": username,
            "status": user['status'],
            "quota_bytes": quota_info['quota_bytes'] if quota_info else 0,
            "bytes_used": quota_info['bytes_used'] if quota_info else 0,
            "created_at": user['created_at']
        }
    @get_cache_manager().cached("system_stats", ttl=60)
    def get_system_stats(self) -> Dict[str, Any]:
        total_users = len(self.user_repo.get_all_users())
        active_users = len(self.user_repo.get_active_users())
        online_users = self.user_repo.get_online_users_count()
        total_usage = self.user_repo.get_total_usage()
        return {
            "total_users": total_users,
            "active_users": active_users,
            "online_users": online_users,
            "total_usage_bytes": total_usage
        }
    def get_cached_user_data(self, username: Username) -> Optional[Dict[str, Any]]:
        cache_key = f"user_{username}"
        return self.cache_manager.get("user_data", cache_key)
    def set_cached_user_data(self, username: Username, data: Dict[str, Any]) -> None:
        cache_key = f"user_{username}"
        self.cache_manager.set("user_data", cache_key, data, ttl=300)
    def invalidate_user_cache(self, username: Username) -> None:
        cache_key = f"user_{username}"
        self.cache_manager.delete("user_data", cache_key)
def get_user_service() -> UserService:
    return get_service('user_service')
