from data.user_repository import UserRepository
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import DATABASE_FILE
from core.backup_interface import IBackupable
import os

class UserService(IBackupable):
    """
    Handles business logic for user management.
    This service now also implements IBackupable to manage the backup of its own critical assets,
    namely the application's database file.
    """
    def __init__(self, user_repo: UserRepository, openvpn_manager: OpenVPNManager, login_manager: LoginUserManager):
        self.user_repo = user_repo
        self.openvpn_manager = openvpn_manager
        self.login_manager = login_manager

    def create_user(self, username, password=None):
        """Creates a new user, generating both a certificate and a system user if needed."""
        print(f"Creating user '{username}'...")
        
        # 1. Create certificate-based user
        self.openvpn_manager.create_user_certificate(username)
        client_config = self.openvpn_manager.generate_user_config(username)
        self.user_repo.add_user(username, "certificate", client_config)
        
        # 2. Create login-based user (if password is provided)
        if password:
            self.login_manager.add_user(username, password)
            # We don't store login-based configs in DB as they are generic
            self.user_repo.add_user(username, "login", "uses_system_auth")

        print(f"✅ User '{username}' created successfully.")
        return client_config

    def remove_user(self, username):
        """Removes a user from all systems (certificate and system user)."""
        print(f"Removing user '{username}'...")
        
        # 1. Revoke certificate
        self.openvpn_manager.revoke_user_certificate(username)
        
        # 2. Remove system user
        self.login_manager.remove_user(username)

        # 3. Remove from database
        self.user_repo.remove_user(username)
        
        print(f"✅ User '{username}' removed successfully.")

    def get_all_users(self):
        """Retrieves all users from the database."""
        return self.user_repo.get_all_users()

    def get_user_config(self, username):
        """Retrieves a specific user's certificate-based configuration."""
        user = self.user_repo.get_user_by_username(username, auth_type="certificate")
        if user:
            return user.get("config_data")
        return None

    # --- IBackupable Interface Implementation ---

    def get_backup_assets(self) -> list[str]:
        """
        Returns the list of critical assets for this service to be backed up.
        For UserService, this is the main application database.
        """
        # Ensure the database file exists before adding it to the asset list.
        if os.path.exists(DATABASE_FILE):
            return [DATABASE_FILE]
        return []

    def pre_restore(self):
        """
        No specific action is needed for the database file before restore,
        as services will be stopped by OpenVPNManager.
        """
        pass

    def post_restore(self):
        """
        Ensures the restored database file has correct ownership and permissions.
        This is critical for security and application function.
        """
        if os.path.exists(DATABASE_FILE):
            print("... Setting permissions for application database...")
            # The database should be owned by root and readable/writable only by root.
            os.chown(DATABASE_FILE, 0, 0)  # owner: root, group: root
            os.chmod(DATABASE_FILE, 0o600)  # permissions: -rw-------
