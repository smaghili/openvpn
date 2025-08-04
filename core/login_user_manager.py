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
            
            # --- DEBUGGING CODE START ---
            password_input_str = f"{username}:{password}"
            print(f"--- DEBUG INFO ---")
            print(f"Data before encoding: {password_input_str}")
            print(f"Type before encoding: {type(password_input_str)}")
            
            password_input_bytes = password_input_str.encode('utf-8')
            
            print(f"Data after encoding: {password_input_bytes}")
            print(f"Type after encoding: {type(password_input_bytes)}")
            print(f"--- END DEBUG INFO ---")
            # --- DEBUGGING CODE END ---

            subprocess.run(
                ["chpasswd"],
                input=password_input_bytes,
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            # Provide a more helpful error message if the user already exists
            if "already exists" in e.stderr.lower():
                print(f"      -> Warning: System user '{username}' already exists. Skipping creation.")
            else:
                raise RuntimeError(f"Failed to add system user '{username}': {e.stderr}")

    def remove_user(self, username: str):
        """
        Removes an existing system user silently.
        Standard output and error are redirected to DEVNULL to suppress messages.
        """
        try:
            # userdel will fail if the user doesn't exist, which is fine.
            # We redirect stdout and stderr to os.devnull to keep the output clean.
            subprocess.run(
                ["userdel", "-r", username],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            # We don't want to stop the main process for any reason here.
            pass

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
