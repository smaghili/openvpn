from data.user_repository import UserRepository
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import DATABASE_FILE
from core.backup_interface import IBackupable
import os
import hashlib

class UserService(IBackupable):
    def __init__(self, user_repo: UserRepository, openvpn_manager: OpenVPNManager, login_manager: LoginUserManager):
        self.user_repo = user_repo
        self.openvpn_manager = openvpn_manager
        self.login_manager = login_manager

    def create_user(self, username, password=None):
        print(f"Creating user '{username}' with dual authentication support...")
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user_id = self.user_repo.add_user(username, password_hash)
        if not user_id:
            raise RuntimeError(f"Failed to create user record for '{username}'")
        
        self.openvpn_manager.create_user_certificate(username)
        
        cert_content = self.openvpn_manager._extract_certificate(f"{self.openvpn_manager.PKI_DIR}/issued/{username}.crt")
        key_content = self.openvpn_manager._read_file(f"{self.openvpn_manager.PKI_DIR}/private/{username}.key")
        
        if not cert_content or not key_content:
            raise RuntimeError(f"Failed to generate certificate for '{username}'")
        
        self.user_repo.add_user_protocol(user_id, "openvpn", "certificate", cert_content, key_content)
        
        if password:
            self.login_manager.add_user(username, password)
            self.user_repo.add_user_protocol(user_id, "openvpn", "login")
        
        client_config = self.user_repo.get_user_certificate_config(username)
        
        print(f"✅ User '{username}' created successfully with dual authentication.")
        return client_config

    def remove_user(self, username):
        db_user_records = self.user_repo.get_user_by_username(username)
        if not db_user_records:
            print(f"User '{username}' not found.")
            return

        print(f"Removing user '{username}'...")
        
        self.openvpn_manager.revoke_user_certificate(username)
        self.login_manager.remove_user(username)
        self.user_repo.remove_user(username)
        
        print(f"✅ User '{username}' removed successfully.")

    def get_all_users(self):
        return self.user_repo.get_all_users()

    def get_user_config(self, username: str):
        return self.user_repo.get_user_certificate_config(username)
        
    def get_shared_config(self):
        return self.openvpn_manager.get_shared_config()

    def get_backup_assets(self) -> list[str]:
        if os.path.exists(DATABASE_FILE):
            return [DATABASE_FILE]
        return []

    def pre_restore(self):
        pass

    def post_restore(self):
        if os.path.exists(DATABASE_FILE):
            print("... Setting permissions for application database...")
            os.chown(DATABASE_FILE, 0, 0)
            os.chmod(DATABASE_FILE, 0o600)
