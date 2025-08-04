import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from .backup_interface import IBackupable

class BackupService:
    """
    Orchestrates the backup and restore process for all backupable services.
    It is completely protocol-agnostic and relies on the IBackupable interface.
    """

    def __init__(self, backupable_services: list[IBackupable]):
        self.services = backupable_services

    def create_backup(self, password: str, backup_dir: str = "~/"):
        """
        Creates a complete, encrypted backup of all registered services.
        1. Gathers all asset paths from the services.
        2. Copies them to a temporary directory.
        3. Creates a single, compressed tarball.
        4. Encrypts the tarball with a password.
        5. Cleans up temporary files.
        """
        print("📦 Creating system-wide backup...")
        backup_path = os.path.expanduser(backup_dir)
        os.makedirs(backup_path, exist_ok=True)
        
        tmp_dir = os.path.join(backup_path, "system_backup_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        try:
            # 1. Gather all assets from all services
            all_assets = []
            for service in self.services:
                all_assets.extend(service.get_backup_assets())

            # 2. Copy assets to the temporary directory
            for asset_path in all_assets:
                if os.path.exists(asset_path):
                    destination = os.path.join(tmp_dir, os.path.basename(asset_path))
                    if os.path.isdir(asset_path):
                        shutil.copytree(asset_path, destination)
                    else:
                        shutil.copy2(asset_path, destination)
                else:
                    print(f"⚠️  Warning: Asset not found and will be skipped: {asset_path}")

            # 3. Create a compressed tarball
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            tar_filename = f"system_backup_{timestamp}.tar.gz"
            tar_path = os.path.join(backup_path, tar_filename)
            print(f"🗜️ Compressing assets into {tar_filename}...")
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(tmp_dir, arcname='.') # Add contents directly

            # 4. Encrypt the tarball
            print("🔒 Encrypting backup file...")
            gpg_filename = f"{tar_path}.gpg"
            gpg_command = [
                "gpg", "--batch", "--yes", "-c",
                "--passphrase-fd", "0", # Read passphrase from stdin
                "-o", gpg_filename,
                tar_path
            ]
            # Use Popen to securely pass the password via stdin
            process = subprocess.Popen(gpg_command, stdin=subprocess.PIPE, text=True)
            process.communicate(input=password)
            if process.returncode != 0:
                raise RuntimeError("GPG encryption failed.")

            # 5. Clean up
            os.remove(tar_path)
            shutil.rmtree(tmp_dir)
            
            print(f"✅ Backup successful! Encrypted file saved to: {gpg_filename}")
            return gpg_filename
        
        except Exception as e:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            raise RuntimeError(f"Backup creation failed: {e}")

    def restore_from_backup(self, gpg_path: str, password: str):
        """
        Restores the entire system from an encrypted backup.
        1. Calls the pre-restore hook for all services (e.g., to stop daemons).
        2. Decrypts and extracts the backup file.
        3. Replaces system files with the backup contents.
        4. Calls the post-restore hook for all services (e.g., to set permissions and restart daemons).
        """
        print("🔄 Restoring system from backup...")
        gpg_path = os.path.expanduser(gpg_path)
        if not os.path.exists(gpg_path):
            raise FileNotFoundError(f"Backup file not found: {gpg_path}")

        tmp_dir = "/tmp/system_restore_tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)
        
        tar_path = os.path.join(tmp_dir, "backup.tar.gz")

        try:
            # 1. Decrypt the backup file securely
            print("🔑 Decrypting backup...")
            gpg_command = [
                "gpg", "--batch", "--yes", "--decrypt",
                "--passphrase-fd", "0", # Read passphrase from stdin
                "-o", tar_path,
                gpg_path
            ]
            process = subprocess.Popen(gpg_command, stdin=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
            _, stderr = process.communicate(input=password)
            if process.returncode != 0:
                if "bad passphrase" in stderr:
                    raise ValueError("Decryption failed. Incorrect password.")
                raise RuntimeError(f"GPG decryption failed: {stderr}")

            # 2. Call pre-restore hooks
            print("⚙️ Preparing system for restore (stopping services)...")
            for service in self.services:
                service.pre_restore()

            # 3. Extract the tarball and replace files
            print("📦 Extracting and restoring files...")
            extract_dir = os.path.join(tmp_dir, "extracted")
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            for item in os.listdir(extract_dir):
                src_path = os.path.join(extract_dir, item)
                dest_path = f"/{item}" if item.startswith("etc") else f"./{item}"
                
                # Clean up destination before moving
                if os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                elif os.path.isfile(dest_path):
                    os.remove(dest_path)

                shutil.move(src_path, dest_path)

            # 4. Call post-restore hooks
            print("🚀 Finalizing restore (restarting services)...")
            for service in self.services:
                service.post_restore()

            print("✅ Restore successful! System is back online.")
        
        finally:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
