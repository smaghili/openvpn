from typing import Optional, List, Dict, Any
from data.user_repository import UserRepository
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import DATABASE_FILE
from core.backup_interface import IBackupable
from core.types import Username, Password, ConfigData, UserData
from core.exceptions import (
    UserAlreadyExistsError, 
    UserNotFoundError, 
    CertificateGenerationError,
    DatabaseError
)
import os
import hashlib

class UserService(IBackupable):
    def __init__(self, user_repo: UserRepository, openvpn_manager: OpenVPNManager, login_manager: LoginUserManager) -> None:
        self.user_repo = user_repo
        self.openvpn_manager = openvpn_manager
        self.login_manager = login_manager

    def create_user(self, username: Username, password: Optional[Password] = None) -> ConfigData:
        print(f"Creating user '{username}' with dual authentication support...")
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check if user already exists
        existing_user = self.user_repo.get_user_by_username(username)
        if existing_user:
            raise UserAlreadyExistsError(username)
        
        try:
            user_id = self.user_repo.add_user(username, password_hash)
            if not user_id:
                raise DatabaseError(f"Failed to create user record for '{username}'")
        except Exception as e:
            raise DatabaseError(f"Database error while creating user '{username}': {e}")
        
        self.openvpn_manager.create_user_certificate(username)
        
        cert_content = self.openvpn_manager._extract_certificate(f"{self.openvpn_manager.PKI_DIR}/issued/{username}.crt")
        key_content = self.openvpn_manager._read_file(f"{self.openvpn_manager.PKI_DIR}/private/{username}.key")
        
        if not cert_content or not key_content:
            raise CertificateGenerationError(username, "Certificate or key content is empty")
        
        self.user_repo.add_user_protocol(user_id, "openvpn", "certificate", cert_content, key_content)
        
        if password:
            self.login_manager.add_user(username, password)
            self.user_repo.add_user_protocol(user_id, "openvpn", "login")
        
        client_config = self.user_repo.get_user_certificate_config(username)
        
        print(f"✅ User '{username}' created successfully with dual authentication.")
        return client_config

    def remove_user(self, username: Username) -> None:
        db_user_records = self.user_repo.get_user_by_username(username)
        if not db_user_records:
            raise UserNotFoundError(username)

        print(f"Removing user '{username}'...")
        
        self.openvpn_manager.revoke_user_certificate(username)
        self.login_manager.remove_user(username)
        self.user_repo.remove_user(username)
        
        print(f"✅ User '{username}' removed successfully.")

    def get_all_users(self) -> List[Dict[str, Any]]:
        return self.user_repo.get_all_users()

    def get_user_config(self, username: Username) -> Optional[ConfigData]:
        return self.user_repo.get_user_certificate_config(username)
        
    def get_shared_config(self) -> ConfigData:
        return self.openvpn_manager.get_shared_config()

    def get_backup_assets(self) -> List[str]:
        if os.path.exists(DATABASE_FILE):
            return [DATABASE_FILE]
        return []

    def pre_restore(self) -> None:
        pass

    def post_restore(self) -> None:
        if os.path.exists(DATABASE_FILE):
            print("... Setting permissions for application database...")
            os.chown(DATABASE_FILE, 0, 0)
            os.chmod(DATABASE_FILE, 0o600)
