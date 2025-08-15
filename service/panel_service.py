"""
Panel configuration service for managing admin credentials and API port.
"""
import os
import secrets
import string
from typing import Dict, Any, Optional
from data.admin_repository import AdminRepository
from core.exceptions import ValidationError, UserNotFoundError

class PanelService:
    """
    Service for managing panel configuration (admin credentials and port).
    """
    
    def __init__(self, admin_repo: AdminRepository):
        self.admin_repo = admin_repo
        self.env_file = ".env"
    
    def change_admin_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """
        Update admin credentials for panel access.
        """
        username, password = self._validate_credentials(username, password)
        
        admin = self.admin_repo.get_admin_by_username("admin")
        if not admin:
            raise UserNotFoundError("Default admin user not found")
        
        self.admin_repo.update_admin_password(admin['id'], password)
        self.admin_repo.update_admin_username(admin['id'], username)
        
        return {
            'username': username,
            'message': 'Admin credentials updated successfully'
        }
    
    def generate_random_credentials(self) -> Dict[str, str]:
        """
        Generate random admin credentials.
        """
        username = self._generate_random_username()
        password = self._generate_random_password()
        
        return {
            'username': username,
            'password': password
        }
    
    def change_panel_port(self, port: int) -> Dict[str, Any]:
        """
        Update API panel port in environment configuration.
        """
        if not self._validate_port(port):
            raise ValidationError(f"Invalid port number: {port}")
        
        self._update_env_variable("API_PORT", str(port))
        
        return {
            'port': port,
            'message': 'Panel port updated successfully. Restart required.'
        }
    
    def generate_random_port(self) -> int:
        """
        Generate random available port for panel.
        """
        return secrets.randbelow(55535) + 10000
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current panel configuration.
        """
        admin = self.admin_repo.get_admin_by_username("admin")
        port = self._get_env_variable("API_PORT") or "5000"
        
        return {
            'username': admin['username'] if admin else 'admin',
            'port': int(port)
        }
    
    def _validate_credentials(self, username: str, password: str) -> tuple[str, str]:
        """
        Validate admin credentials format.
        """
        username = username.strip()
        password = password.strip()
        
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")
        if len(username) > 32:
            raise ValidationError("Username must not exceed 32 characters")
        if len(password) < 4:
            raise ValidationError("Password must be at least 4 characters")
        if len(password) > 128:
            raise ValidationError("Password must not exceed 128 characters")
        
        return username, password
    
    def _validate_port(self, port: int) -> bool:
        """
        Validate port number range.
        """
        return 1024 <= port <= 65535
    
    def _generate_random_username(self) -> str:
        """
        Generate random username.
        """
        prefixes = ['admin', 'manager', 'panel', 'vpn']
        prefix = secrets.choice(prefixes)
        suffix = ''.join(secrets.choice(string.digits) for _ in range(3))
        return f"{prefix}{suffix}"
    
    def _generate_random_password(self) -> str:
        """
        Generate secure random password.
        """
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(12))
    
    def _update_env_variable(self, key: str, value: str) -> None:
        """
        Update environment variable in .env file.
        """
        env_lines = []
        key_found = False
        
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        env_lines.append(f"{key}={value}\n")
                        key_found = True
                    else:
                        env_lines.append(line)
        
        if not key_found:
            env_lines.append(f"{key}={value}\n")
        
        with open(self.env_file, 'w') as f:
            f.writelines(env_lines)
    
    def _get_env_variable(self, key: str) -> Optional[str]:
        """
        Get environment variable from .env file.
        """
        if not os.path.exists(self.env_file):
            return None
        
        with open(self.env_file, 'r') as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    return line.strip().split('=', 1)[1]
        
        return None