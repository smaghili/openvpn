"""
Secure storage service for sensitive data like backup passwords.
Uses system keyring for secure, encrypted storage.
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class SecureStorageService:
    """
    Secure storage service for sensitive application data.
    Uses file-based encrypted storage with PBKDF2 key derivation.
    """
    
    STORAGE_DIR = "/var/lib/owpanel/secure"
    SALT_FILE = os.path.join(STORAGE_DIR, ".salt")
    
    def __init__(self):
        self._ensure_storage_directory()
        self._master_key = self._get_or_create_master_key()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure secure storage directory exists with proper permissions."""
        os.makedirs(self.STORAGE_DIR, mode=0o700, exist_ok=True)
        
        # Ensure proper ownership and permissions
        try:
            os.chown(self.STORAGE_DIR, 0, 0)  # root:root
            os.chmod(self.STORAGE_DIR, 0o700)  # rwx------
        except (OSError, PermissionError):
            logger.warning("Could not set secure permissions on storage directory")
    
    def _get_or_create_master_key(self) -> bytes:
        """Generate or retrieve master encryption key."""
        try:
            if os.path.exists(self.SALT_FILE):
                with open(self.SALT_FILE, 'rb') as f:
                    salt = f.read()
            else:
                salt = os.urandom(16)
                with open(self.SALT_FILE, 'wb') as f:
                    f.write(salt)
                os.chmod(self.SALT_FILE, 0o600)
            
            # Derive key from system entropy and salt
            machine_id = self._get_machine_identifier()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
            return key
            
        except Exception as e:
            logger.error(f"Failed to generate master key: {e}")
            raise RuntimeError("Secure storage initialization failed")
    
    def _get_machine_identifier(self) -> str:
        """Get a stable machine identifier for key derivation."""
        try:
            # Try to get machine-id first
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            
            # Fallback to hostname + some system info
            import socket
            hostname = socket.gethostname()
            return f"owpanel-{hostname}-backup-key"
            
        except Exception:
            return "owpanel-default-backup-key"
    
    def store_password(self, admin_id: int, password: str) -> bool:
        """Store backup password securely for an admin user."""
        try:
            fernet = Fernet(self._master_key)
            encrypted_password = fernet.encrypt(password.encode('utf-8'))
            
            password_file = os.path.join(self.STORAGE_DIR, f"backup_pass_{admin_id}")
            with open(password_file, 'wb') as f:
                f.write(encrypted_password)
            
            os.chmod(password_file, 0o600)
            logger.info(f"Backup password stored securely for admin {admin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store backup password: {e}")
            return False
    
    def get_password(self, admin_id: int) -> Optional[str]:
        """Retrieve stored backup password for an admin user."""
        try:
            password_file = os.path.join(self.STORAGE_DIR, f"backup_pass_{admin_id}")
            
            if not os.path.exists(password_file):
                return None
            
            with open(password_file, 'rb') as f:
                encrypted_password = f.read()
            
            fernet = Fernet(self._master_key)
            password = fernet.decrypt(encrypted_password).decode('utf-8')
            
            logger.info(f"Backup password retrieved for admin {admin_id}")
            return password
            
        except Exception as e:
            logger.error(f"Failed to retrieve backup password: {e}")
            return None
    
    def delete_password(self, admin_id: int) -> bool:
        """Delete stored backup password for an admin user."""
        try:
            password_file = os.path.join(self.STORAGE_DIR, f"backup_pass_{admin_id}")
            
            if os.path.exists(password_file):
                os.remove(password_file)
                logger.info(f"Backup password deleted for admin {admin_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup password: {e}")
            return False
    
    def has_stored_password(self, admin_id: int) -> bool:
        """Check if admin has a stored backup password."""
        password_file = os.path.join(self.STORAGE_DIR, f"backup_pass_{admin_id}")
        return os.path.exists(password_file)