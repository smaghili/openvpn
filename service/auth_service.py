"""
Authentication service orchestrating JWT authentication and security controls.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.blacklist_repository import BlacklistRepository
from core.jwt_service import JWTService
from core.exceptions import AuthenticationError, ValidationError, UserNotFoundError
import re
import time
import threading

class AuthService:
    """
    Service layer for authentication operations with comprehensive security.
    """
    
    def __init__(self, admin_repo: AdminRepository, permission_repo: PermissionRepository,
                 blacklist_repo: BlacklistRepository, jwt_service: JWTService):
        self.admin_repo = admin_repo
        self.permission_repo = permission_repo
        self.blacklist_repo = blacklist_repo
        self.jwt_service = jwt_service
        self._rate_limits = {'login': {}, 'admin': {}}
        self._start_cleanup_task()

    def _start_cleanup_task(self, interval: int = 60) -> None:
        def _cleanup_loop() -> None:
            while True:
                time.sleep(interval)
                self.cleanup_rate_limits()

        thread = threading.Thread(target=_cleanup_loop, daemon=True)
        thread.start()
    
    def login(self, username: str, password: str, client_ip: str) -> Dict[str, Any]:
        """
        Authenticate admin user and generate JWT token with rate limiting.
        """
        username, password = self._validate_credentials(username, password)
        
        if not self._check_login_rate_limit(client_ip):
            raise AuthenticationError("Too many login attempts. Please try again later.")
        
        admin = self.admin_repo.verify_password(username, password)
        if not admin:
            raise AuthenticationError("Invalid username or password")
        
        token_data = self.jwt_service.generate_token(
            admin['id'],
            admin['username'],
            admin['role'],
            admin['token_version']
        )

        result = {
            'token': token_data['token'],
            'role': admin['role'],
            'expires_in': token_data['expires_in'],
            'username': admin['username']
        }

        self.cleanup_rate_limits()
        return result
    
    def logout(self, token: str) -> Dict[str, Any]:
        payload = self.jwt_service.validate_token(token)
        token_id = payload['jti']
        admin_id = payload['admin_id']
        exp_timestamp = payload['exp']
        expires_at = datetime.fromtimestamp(exp_timestamp)
        self.jwt_service.blacklist_token(token_id)
        self.blacklist_repo.blacklist_token(token_id, admin_id, expires_at)
        return {
            'success': True,
            'message': 'Logged out successfully'
        }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token with comprehensive security checks.
        """
        payload = self.jwt_service.validate_token(token)
        
        admin = self.admin_repo.get_admin_by_id(payload['admin_id'])
        if not admin:
            raise AuthenticationError("Admin user not found")
        
        if not self.jwt_service.validate_token_version(payload['token_version'], admin['token_version']):
            raise AuthenticationError("Token version invalid - please login again")
        
        if self.blacklist_repo.is_token_blacklisted(payload['jti']):
            raise AuthenticationError("Token has been revoked")
        
        return {
            'admin_id': admin['id'],
            'username': admin['username'],
            'role': admin['role'],
            'token_version': admin['token_version']
        }
    
    def check_permission(self, admin_id: int, permission: str) -> bool:
        """
        Check admin permission with real-time database validation.
        """
        has_permission = self.permission_repo.has_permission(admin_id, permission)
        self.cleanup_rate_limits()
        return has_permission
    
    def force_logout_admin(self, admin_id: int, by_admin_id: int) -> Dict[str, Any]:
        if not self.check_permission(by_admin_id, 'tokens:revoke'):
            raise AuthenticationError("Insufficient permissions to revoke tokens")
        self.admin_repo.increment_token_version(admin_id)
        expires_at = datetime.now() + timedelta(days=1)
        self.blacklist_repo.blacklist_all_admin_tokens(admin_id, expires_at)
        return {
            'success': True,
            'message': 'All admin sessions revoked successfully'
        }
    
    def change_password(self, admin_id: int, current_password: str, new_password: str, by_admin_id: int) -> None:
        """
        Change admin password with validation and forced re-login.
        """
        if admin_id != by_admin_id:
            if not self.check_permission(by_admin_id, 'admins:update'):
                raise AuthenticationError("Insufficient permissions to change password")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        if admin_id == by_admin_id:
            if not self.admin_repo.verify_password(admin['username'], current_password):
                raise AuthenticationError("Current password is incorrect")
        
        self._validate_password(new_password)
        
        if current_password == new_password:
            raise ValidationError("New password must be different from current password")
        
        self.admin_repo.update_password(admin_id, new_password)
    
    def _validate_credentials(self, username: str, password: str) -> tuple:
        """
        Validate login credentials format and security.
        """
        username = str(username).strip()[:50] if username else ""
        password = str(password)[:100] if password else ""
        
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        if len(username) < 3 or len(username) > 50:
            raise ValidationError("Username must be 3-50 characters")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username contains invalid characters")
        
        return username, password
    
    def _validate_password(self, password: str) -> None:
        """
        Validate password strength requirements.
        """
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if len(password) > 100:
            raise ValidationError("Password too long (max 100 characters)")
    
    def _check_login_rate_limit(self, client_ip: str, max_attempts: int = 5, window_minutes: int = 10) -> bool:
        """
        Check login rate limiting per IP address.
        """
        now = time.time()
        window_seconds = window_minutes * 60
        
        if client_ip not in self._rate_limits['login']:
            self._rate_limits['login'][client_ip] = []
        
        attempts = self._rate_limits['login'][client_ip]
        attempts = [timestamp for timestamp in attempts if now - timestamp < window_seconds]
        
        if len(attempts) >= max_attempts:
            return False
        
        attempts.append(now)
        self._rate_limits['login'][client_ip] = attempts
        return True
    
    def check_admin_rate_limit(self, admin_id: int, max_requests: int = 100, window_minutes: int = 1) -> bool:
        """
        Check rate limiting for admin operations.
        """
        now = time.time()
        window_seconds = window_minutes * 60
        
        if admin_id not in self._rate_limits['admin']:
            self._rate_limits['admin'][admin_id] = []
        
        requests = self._rate_limits['admin'][admin_id]
        requests = [timestamp for timestamp in requests if now - timestamp < window_seconds]
        
        if len(requests) >= max_requests:
            return False
        
        requests.append(now)
        self._rate_limits['admin'][admin_id] = requests
        return True
    
    def cleanup_rate_limits(self) -> None:
        """
        Clean up expired rate limit entries to prevent memory growth.
        """
        now = time.time()
        
        for rate_type in self._rate_limits:
            for key in list(self._rate_limits[rate_type].keys()):
                attempts = self._rate_limits[rate_type][key]
                attempts = [timestamp for timestamp in attempts if now - timestamp < 3600]
                
                if attempts:
                    self._rate_limits[rate_type][key] = attempts
                else:
                    del self._rate_limits[rate_type][key]
