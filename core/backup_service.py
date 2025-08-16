import os
import shutil
import subprocess
import tarfile
import logging
from datetime import datetime
from typing import List
from .backup_interface import IBackupable
from core.exceptions import BackupError, RestoreError

logger = logging.getLogger(__name__)

class BackupService:
    """
    Orchestrates the backup and restore process for all backupable services.
    It is completely protocol-agnostic and relies on the IBackupable interface.
    """

    def __init__(self, backupable_services: List[IBackupable]) -> None:
        self.services = backupable_services

    def create_backup(self, password: str, backup_dir: str = "~/") -> str:
        """
        Creates a complete, encrypted backup of all registered services.
        1. Gathers all asset paths from the services.
        2. Copies them to a temporary directory.
        3. Creates a single, compressed tarball.
        4. Encrypts the tarball with a password.
        5. Cleans up temporary files.
        """
        logger.info("📦 Creating backup...")
        backup_path = os.path.expanduser(backup_dir)
        os.makedirs(backup_path, exist_ok=True)
        
        tmp_dir = os.path.join(backup_path, "system_backup_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        try:
            all_assets = []
            for service in self.services:
                all_assets.extend(service.get_backup_assets())

            for asset_path in all_assets:
                if os.path.exists(asset_path):
                    dest_path = os.path.join(tmp_dir, asset_path.lstrip('/'))
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    if os.path.isdir(asset_path):
                        shutil.copytree(asset_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(asset_path, dest_path)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            tar_filename = f"system_backup_{timestamp}.tar.gz"
            tar_path = os.path.join(backup_path, tar_filename)
            
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(tmp_dir, arcname='/')

            gpg_filename = f"{tar_path}.gpg"
            gpg_command = [
                "gpg", "--batch", "--yes", "-c",
                "--passphrase-fd", "0",
                "-o", gpg_filename,
                tar_path
            ]
            process = subprocess.Popen(gpg_command, stdin=subprocess.PIPE, text=True)
            process.communicate(input=password)
            if process.returncode != 0:
                raise BackupError("GPG encryption failed")

            os.remove(tar_path)
            shutil.rmtree(tmp_dir)

            logger.info("✅ Backup created: %s", gpg_filename)
            return gpg_filename
        
        except Exception as e:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            raise BackupError(f"Backup creation failed: {e}")

    def restore_system(self, gpg_path: str, password: str) -> None:
        """
        Restores the entire system from an encrypted backup.
        1. Calls the pre-restore hook for all services (e.g., to stop daemons).
        2. Decrypts and extracts the backup file.
        3. Replaces system files with the backup contents.
        4. Calls the post-restore hook for all services (e.g., to set permissions and restart daemons).
        """
        logger.info("🔄 Restoring from backup...")
        gpg_path = os.path.expanduser(gpg_path)
        if not os.path.exists(gpg_path):
            raise RestoreError(f"Backup file not found: {gpg_path}")

        tmp_dir = "/tmp/system_restore_tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)
        
        tar_path = os.path.join(tmp_dir, "backup.tar.gz")

        try:
            gpg_command = [
                "gpg", "--batch", "--yes", "--decrypt",
                "--passphrase-fd", "0",
                "-o", tar_path,
                gpg_path
            ]
            process = subprocess.Popen(gpg_command, stdin=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
            _, stderr = process.communicate(input=password)
            if process.returncode != 0:
                if "bad passphrase" in stderr.lower():
                    raise RestoreError("Decryption failed. Incorrect password.")
                raise RestoreError(f"GPG decryption failed: {stderr}")

            for service in self.services:
                service.pre_restore()

            with tarfile.open(tar_path, "r:gz") as tar:
                self._safe_extract(tar, path="/")

            for service in self.services:
                service.post_restore()

            logger.info("✅ Restore completed successfully")
        
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    @staticmethod
    def _safe_extract(tar: tarfile.TarFile, path: str = ".") -> None:
        """Safely extract a tar archive, preventing path traversal attacks."""
        abs_path = os.path.abspath(path)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(path, member.name))
            if not member_path.startswith(abs_path):
                raise RestoreError("Attempted Path Traversal in Tar File")
        tar.extractall(path)
