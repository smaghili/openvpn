import subprocess
import os
import shutil
from typing import List
from .backup_interface import IBackupable
from core.types import Username, Password
from core.exceptions import ServiceError
from core.logging_config import LoggerMixin

class LoginUserManager(IBackupable, LoggerMixin):
    SYSTEM_USER_FILES = ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]

    def add_user(self, username: Username, password: Password) -> None:
        try:
            subprocess.run(
                ["useradd", "-M", "-s", "/usr/sbin/nologin", username],
                check=True, capture_output=True
            )
            subprocess.run(
                ["chpasswd"],
                input=f"{username}:{password}",
                text=True,
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            if "already exists" in stderr_text.lower():
                pass
            else:
                raise RuntimeError(f"Failed to add system user '{username}': {stderr_text}")

    def remove_user(self, username: Username) -> None:
        try:
            subprocess.run(
                ["userdel", "-r", username],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def change_user_password(self, username: Username, new_password: Password) -> None:
        try:
            subprocess.run(
                ["chpasswd"],
                input=f"{username}:{new_password}",
                text=True,
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            raise ServiceError(
                "chpasswd",
                f"change password for system user '{username}'",
                stderr_text,
            )



    def get_backup_assets(self) -> List[str]:
        return self.SYSTEM_USER_FILES

    def pre_restore(self) -> None:
        pass

    def post_restore(self) -> None:
        for f_path in self.SYSTEM_USER_FILES:
            if os.path.exists(f_path):
                shutil.chown(f_path, "root", "root")
                if "shadow" in f_path or "gshadow" in f_path:
                    os.chmod(f_path, 0o640)
                else:
                    os.chmod(f_path, 0o644)
