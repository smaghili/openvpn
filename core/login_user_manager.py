import subprocess
from .backup_interface import IBackupable

class LoginUserManager(IBackupable):
    """
    Manages Linux system users for OpenVPN's PAM module.
    It adds/removes system users and declares critical system files for backup.
    """

    def get_backup_assets(self) -> list[str]:
        """Returns the list of files essential for user authentication."""
        # These files contain all user, group, and password information.
        return ["/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow"]

    def pre_restore(self):
        """No services to stop for user management, so this does nothing."""
        pass

    def post_restore(self):
        """
        After restoring user files, it's crucial to ensure permissions are correct
        for security.
        """
        print("...Securing user authentication files...")
        subprocess.run(["chmod", "644", "/etc/passwd"], check=False)
        subprocess.run(["chmod", "640", "/etc/shadow"], check=False)
        subprocess.run(["chmod", "644", "/etc/group"], check=False)
        subprocess.run(["chmod", "640", "/etc/gshadow"], check=False)

    def add_user(self, username: str, password: str):
        """Adds a new system user with a disabled shell and sets their password."""
        try:
            subprocess.run(
                ["useradd", "-M", "-s", "/usr/sbin/nologin", username],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            if "already exists" not in e.stderr:
                raise RuntimeError(f"Failed to create system user '{username}': {e.stderr}")

        password_process = subprocess.Popen(
            ["chpasswd"], stdin=subprocess.PIPE, text=True, stderr=subprocess.PIPE
        )
        _, stderr = password_process.communicate(input=f"{username}:{password}")
        if password_process.returncode != 0:
            raise RuntimeError(f"Failed to set password for user '{username}': {stderr}")

    def remove_user(self, username: str):
        """Removes a system user, failing silently if they don't exist."""
        try:
            subprocess.run(
                ["userdel", username], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            pass
