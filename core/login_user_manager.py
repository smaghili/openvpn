import subprocess
import os
import shutil
from typing import List
from .backup_interface import IBackupable
from core.types import Username, Password
from core.exceptions import ServiceError

class LoginUserManager(IBackupable):
    """
    Manages Linux system users for OpenVPN's PAM (Password Authentication) module.
    Its sole responsibility is to add and remove system users with a non-interactive shell.
    It also provides system user files for backup/restore.
    """


    SYSTEM_USER_FILES = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]

    def add_user(self, username: Username, password: Password) -> None:
        """
        Adds a new system user with a non-interactive shell.
        This user is intended for services like VPN, not for direct SSH login.
        """
        try:
            subprocess.run(
                ["useradd", "-M", "-s", "/usr/sbin/nologin", username],
                check=True, capture_output=True
            )
            subprocess.run(
                ["chpasswd"],
                input=f"{username}:{password}".encode('utf-8'),
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            if "already exists" in stderr_text.lower():
                print(f"⚠️  Warning: System user '{username}' already exists")
            else:
                raise RuntimeError(f"Failed to add system user '{username}': {stderr_text}")

    def remove_user(self, username: Username) -> None:
        """
        Removes an existing system user silently.
        Standard output and error are redirected to DEVNULL to suppress messages.
        """
        try:
            subprocess.run(
                ["userdel", "-r", username],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass



    def get_backup_assets(self) -> List[str]:
        """Returns the list of critical system user files for backup."""
        return self.SYSTEM_USER_FILES

    def pre_restore(self) -> None:
        """
        No specific pre-restore action needed for these files, as critical services
        are handled by the OpenVPNManager.
        """
        pass

    def post_restore(self) -> None:
        """
        Ensures correct, secure permissions on the restored system user files.
        This is a critical security step.
        """
        for f_path in self.SYSTEM_USER_FILES:
            if os.path.exists(f_path):
                shutil.chown(f_path, "root", "root")
                if "shadow" in f_path or "gshadow" in f_path:
                    os.chmod(f_path, 0o640)
                else:
                    os.chmod(f_path, 0o644)
