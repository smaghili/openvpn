import subprocess
import os
import shutil
from .backup_interface import IBackupable

class LoginUserManager(IBackupable):
    """
    Manages Linux system users for OpenVPN's PAM (Password Authentication) module.
    Its sole responsibility is to add and remove system users with a non-interactive shell.
    It also provides system user files for backup/restore.
    """

    # These are the critical files that define system users and groups.
    SYSTEM_USER_FILES = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]

    def add_user(self, username: str, password: str):
        """
        Adds a new system user with a non-interactive shell.
        This user is intended for services like VPN, not for direct SSH login.
        """
        print(f"... Adding system user '{username}' for login authentication")
        try:
            # Create the user with /usr/sbin/nologin to prevent shell access
            subprocess.run(
                ["useradd", "-M", "-s", "/usr/sbin/nologin", username],
                check=True, capture_output=True
            )
            # Set the user's password using chpasswd
            subprocess.run(
                ["chpasswd"],
                input=f"{username}:{password}",
                text=True, check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            # Provide a more helpful error message if the user already exists
            if "already exists" in e.stderr.lower():
                print(f"      -> Warning: System user '{username}' already exists. Skipping creation.")
            else:
                raise RuntimeError(f"Failed to add system user '{username}': {e.stderr}")

    def remove_user(self, username: str):
        """
        Removes an existing system user.
        """
        print(f"... Removing system user '{username}'")
        try:
            # userdel will fail if the user doesn't exist, which is fine.
            subprocess.run(
                ["userdel", "-r", username],
                check=False, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            # We don't want to stop the process if user deletion fails, just warn.
            print(f"      -> Warning: Could not remove system user '{username}': {e.stderr}")

    # --- IBackupable Interface Implementation ---

    def get_backup_assets(self) -> list[str]:
        """Returns the list of critical system user files for backup."""
        return self.SYSTEM_USER_FILES

    def pre_restore(self):
        """
        No specific pre-restore action needed for these files, as critical services
        are handled by the OpenVPNManager.
        """
        pass

    def post_restore(self):
        """
        Ensures correct, secure permissions on the restored system user files.
        This is a critical security step.
        """
        print("... Setting secure permissions for restored system user files...")
        for f_path in self.SYSTEM_USER_FILES:
            if os.path.exists(f_path):
                # Default owner is root:root
                shutil.chown(f_path, "root", "root")
                # Set standard secure permissions
                if "shadow" in f_path or "gshadow" in f_path:
                    os.chmod(f_path, 0o640)  # Readable by root and group shadow
                else:
                    os.chmod(f_path, 0o644)  # Readable by all, writable by root
