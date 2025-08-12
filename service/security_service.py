"""
Security service for rate limiting and validation across the system.
"""

from typing import Dict, Any, List, Optional
import time
import secrets
import threading
from data.user_repository import UserRepository
from data.blacklist_repository import BlacklistRepository
from core.exceptions import ValidationError, AuthenticationError

class SecurityService:
    """
    Service for security controls including rate limiting and profile token management.
    """
    
    def __init__(self, user_repo: UserRepository, blacklist_repo: BlacklistRepository):
        self.user_repo = user_repo
        self.blacklist_repo = blacklist_repo
        self._rate_limits = {'profile': {}, 'ip': {}}
        self._start_cleanup_task()

    def _start_cleanup_task(self, interval: int = 60) -> None:
        def _cleanup_loop() -> None:
            while True:
                time.sleep(interval)
                self.cleanup_rate_limits()

        thread = threading.Thread(target=_cleanup_loop, daemon=True)
        thread.start()
    
    def generate_profile_token(self, user_id: int, admin_id: int, admin_role: str) -> Dict[str, Any]:
        """
        Generate or retrieve profile token for VPN user.
        """
        user = self.user_repo.find_user_by_username(str(user_id))
        if not user:
            raise ValidationError(f"User ID {user_id} not found")
        
        if admin_role != 'admin' and user.get('created_by') != admin_id:
            raise AuthenticationError("Access denied to this user")
        
        if user.get('profile_token'):
            return {
                'profile_token': user['profile_token'],
                'profile_url': f"/profile/{user['profile_token']}",
                'existing': True
            }
        
        profile_token = secrets.token_urlsafe(32)
        
        query = "UPDATE users SET profile_token = ? WHERE id = ?"
        self.user_repo.db.execute_query(query, (profile_token, user_id))
        
        return {
            'profile_token': profile_token,
            'profile_url': f"/profile/{profile_token}",
            'existing': False
        }
    
    def regenerate_profile_token(self, user_id: int, admin_id: int, admin_role: str) -> Dict[str, Any]:
        """
        Regenerate profile token and reset access stats.
        """
        user = self.user_repo.find_user_by_username(str(user_id))
        if not user:
            raise ValidationError(f"User ID {user_id} not found")
        
        if admin_role != 'admin' and user.get('created_by') != admin_id:
            raise AuthenticationError("Access denied to this user")
        
        old_token = user.get('profile_token')
        new_token = secrets.token_urlsafe(32)
        
        query = """
        UPDATE users 
        SET profile_token = ?, profile_access_count = 0, profile_last_accessed = NULL 
        WHERE id = ?
        """
        self.user_repo.db.execute_query(query, (new_token, user_id))
        
        return {
            'profile_token': new_token,
            'profile_url': f"/profile/{new_token}",
            'old_token_revoked': bool(old_token)
        }
    
    def revoke_profile_access(self, user_id: int, admin_id: int, admin_role: str) -> Dict[str, Any]:
        """
        Revoke profile access by removing token.
        """
        user = self.user_repo.find_user_by_username(str(user_id))
        if not user:
            raise ValidationError(f"User ID {user_id} not found")
        
        if admin_role != 'admin' and user.get('created_by') != admin_id:
            raise AuthenticationError("Access denied to this user")
        
        query = """
        UPDATE users 
        SET profile_token = NULL, profile_access_count = 0, profile_last_accessed = NULL 
        WHERE id = ?
        """
        self.user_repo.db.execute_query(query, (user_id,))
        
        return {'message': 'Profile access revoked successfully'}
    
    def get_profile_stats(self, user_id: int, admin_id: int, admin_role: str) -> Dict[str, Any]:
        """
        Get profile access statistics.
        """
        user = self.user_repo.find_user_by_username(str(user_id))
        if not user:
            raise ValidationError(f"User ID {user_id} not found")
        
        if admin_role != 'admin' and user.get('created_by') != admin_id:
            raise AuthenticationError("Access denied to this user")
        
        return {
            'username': user['username'],
            'has_profile_token': bool(user.get('profile_token')),
            'access_count': user.get('profile_access_count', 0),
            'last_accessed': user.get('profile_last_accessed'),
            'profile_created': user.get('created_at') if user.get('profile_token') else None
        }
    
    def validate_profile_access(self, profile_token: str, client_ip: str) -> Dict[str, Any]:
        """
        Validate profile token access with rate limiting.
        """
        if not self.check_profile_rate_limit(client_ip):
            raise AuthenticationError("Too many profile requests. Please try again later.")
        
        query = """
        SELECT id, username, status, profile_token, profile_access_count 
        FROM users 
        WHERE profile_token = ? AND status = 'active'
        """
        result = self.user_repo.db.execute_query(query, (profile_token,))
        
        if not result:
            raise ValidationError("Invalid or expired profile token")
        
        user = result[0]
        
        update_query = """
        UPDATE users 
        SET profile_access_count = profile_access_count + 1, 
            profile_last_accessed = CURRENT_TIMESTAMP 
        WHERE id = ?
        """
        self.user_repo.db.execute_query(update_query, (user['id'],))
        
        return user
    
    def get_profile_data(self, profile_token: str) -> Dict[str, Any]:
        """
        Get public profile data for display.
        """
        query = """
        SELECT 
            u.username, u.status, u.created_at,
            uq.quota_bytes, uq.bytes_used,
            u.profile_access_count, u.profile_last_accessed
        FROM users u
        LEFT JOIN user_quotas uq ON u.id = uq.user_id
        WHERE u.profile_token = ? AND u.status = 'active'
        """
        result = self.user_repo.db.execute_query(query, (profile_token,))
        
        if not result:
            raise ValidationError("Profile not found or inactive")
        
        user_data = result[0]
        
        quota_gb = user_data['quota_bytes'] / (1024**3) if user_data['quota_bytes'] else 0
        used_gb = user_data['bytes_used'] / (1024**3) if user_data['bytes_used'] else 0
        remaining_gb = max(0, quota_gb - used_gb) if quota_gb > 0 else float('inf')
        usage_percent = (used_gb / quota_gb * 100) if quota_gb > 0 else 0
        
        return {
            'username': user_data['username'],
            'status': user_data['status'],
            'quota': {
                'limit_gb': quota_gb,
                'used_gb': round(used_gb, 2),
                'remaining_gb': round(remaining_gb, 2) if remaining_gb != float('inf') else 'unlimited',
                'usage_percent': round(usage_percent, 1)
            },
            'connection': {
                'is_online': False,
                'last_connection': None,
                'total_sessions': 0
            },
            'download_links': {
                'ovpn_config': f"/api/profile/{profile_token}/config.ovpn",
                'qr_code': f"/api/profile/{profile_token}/qr-code"
            },
            'statistics': {
                'total_access_count': user_data['profile_access_count'] or 0,
                'last_accessed': user_data['profile_last_accessed'],
                'profile_created': user_data['created_at']
            }
        }
    
    def check_profile_rate_limit(self, client_ip: str, max_requests: int = 60, window_minutes: int = 1) -> bool:
        """
        Check rate limiting for profile access.
        """
        return self._check_rate_limit('profile', client_ip, max_requests, window_minutes * 60)
    
    def check_ip_rate_limit(self, client_ip: str, max_requests: int = 100, window_minutes: int = 1) -> bool:
        """
        Check general IP-based rate limiting.
        """
        return self._check_rate_limit('ip', client_ip, max_requests, window_minutes * 60)
    
    def _check_rate_limit(self, limit_type: str, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Generic rate limiting implementation.
        """
        now = time.time()
        
        if key not in self._rate_limits[limit_type]:
            self._rate_limits[limit_type][key] = []
        
        requests = self._rate_limits[limit_type][key]
        requests = [timestamp for timestamp in requests if now - timestamp < window_seconds]
        
        if len(requests) >= max_requests:
            return False
        
        requests.append(now)
        self._rate_limits[limit_type][key] = requests

        self.cleanup_rate_limits()
        return True
    
    def cleanup_rate_limits(self) -> None:
        """
        Clean up expired rate limit entries.
        """
        now = time.time()
        
        for limit_type in self._rate_limits:
            for key in list(self._rate_limits[limit_type].keys()):
                requests = self._rate_limits[limit_type][key]
                requests = [timestamp for timestamp in requests if now - timestamp < 3600]
                
                if requests:
                    self._rate_limits[limit_type][key] = requests
                else:
                    del self._rate_limits[limit_type][key]

    def get_security_stats(self) -> Dict[str, Any]:
        """
        Get security statistics for monitoring.
        """
        blacklist_stats = self.blacklist_repo.get_blacklist_stats()
        
        rate_limit_stats = {}
        for limit_type in self._rate_limits:
            rate_limit_stats[limit_type] = {
                'active_keys': len(self._rate_limits[limit_type]),
                'total_requests': sum(len(requests) for requests in self._rate_limits[limit_type].values())
            }
        
        return {
            'blacklist': blacklist_stats,
            'rate_limits': rate_limit_stats
        }
