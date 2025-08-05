from typing import Optional, List, Dict, Any
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
    DatabaseError
)
import os
import hashlib

class UserService(IBackupable):
    def __init__(self, user_repo: UserRepository, openvpn_manager: OpenVPNManager, login_manager: LoginUserManager) -> None:
        self.user_repo = user_repo
        self.openvpn_manager = openvpn_manager
        self.login_manager = login_manager

    def _generate_user_certificate_config(self, username: Username) -> Optional[str]:
        """Generates the OpenVPN client configuration for a user based on their certificate."""
        user_data = self.user_repo.get_user_by_username(username, 'certificate')
        if not user_data or not user_data.get('cert_pem'):
            return None

        ca_cert = self.openvpn_manager._read_file(f"{self.openvpn_manager.OPENVPN_DIR}/ca.crt")
        tls_crypt_key = self.openvpn_manager._read_file(f"{self.openvpn_manager.OPENVPN_DIR}/tls-crypt.key")
        
        user_specific_certs = USER_CERTS_TEMPLATE.format(
            user_cert=user_data['cert_pem'],
            user_key=user_data['key_pem']
        )
        
        return CLIENT_TEMPLATE.format(
            proto=self.openvpn_manager.settings.get("cert_proto", "udp"),
            server_ip=self.openvpn_manager.settings.get("public_ip"),
            port=self.openvpn_manager.settings.get("cert_port", "1194"),
            ca_cert=ca_cert,
            user_specific_certs=user_specific_certs,
            tls_crypt_key=tls_crypt_key
        )

    def create_user(self, username: Username, password: Optional[Password] = None) -> Optional[ConfigData]:
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if self.user_repo.find_user_by_username(username):
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
        
        client_config = self._generate_user_certificate_config(username)
        
        print(f"✅ User '{username}' created successfully")
        return client_config

    def remove_user(self, username: Username, silent: bool = False) -> None:
        if not self.user_repo.find_user_by_username(username):
            raise UserNotFoundError(username)

        if not silent:
            print(f"Removing user '{username}'...")
        
        self.openvpn_manager.revoke_user_certificate(username)
        self.login_manager.remove_user(username)
        self.user_repo.remove_user(username)
        
        if not silent:
            print(f"✅ User '{username}' removed successfully.")

    def get_all_users_with_status(self) -> List[Dict[str, Any]]:
        return self.user_repo.get_all_users_with_details()

    def get_user_config(self, username: Username) -> Optional[ConfigData]:
        return self._generate_user_certificate_config(username)
        
    def get_shared_config(self) -> ConfigData:
        return self.openvpn_manager.get_shared_config()

    # --- New methods for Quota Management ---

    def set_quota_for_user(self, username: Username, quota_gb: float) -> None:
        """Sets the data quota for a specific user."""
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(username)
        
        self.user_repo.set_user_quota(user['id'], quota_gb)
        print(f"✅ Quota for user '{username}' set to {quota_gb} GB (0 for unlimited).")

    def get_user_status(self, username: Username) -> Optional[Dict[str, Any]]:
        """Gets the detailed status including quota and usage for a user."""
        user = self.user_repo.find_user_by_username(username)
        if not user:
            raise UserNotFoundError(username)
        
        return self.user_repo.get_user_quota_status(user['id'])

    # --- Backup and Restore ---

    def get_backup_assets(self) -> List[str]:
        if os.path.exists(DATABASE_FILE):
            return [DATABASE_FILE]
        return []

    def pre_restore(self) -> None:
        pass

    def post_restore(self) -> None:
        if os.path.exists(DATABASE_FILE):
            os.chown(DATABASE_FILE, 0, 0)
            os.chmod(DATABASE_FILE, 0o600)
