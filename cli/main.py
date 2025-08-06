#!/usr/bin/env python3
import os
import sys
import re
from getpass import getpass
import urllib.request
from typing import Dict, Any, Optional

real_script_path = os.path.realpath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(real_script_path), '..'))
os.chdir(project_root)
sys.path.insert(0, project_root)

from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from service.user_service import UserService
from data.db import Database
from data.user_repository import UserRepository
from core.backup_service import BackupService
from config.config import VPNConfig, config, InstallSettings
from core.types import Username
from core.exceptions import (
    VPNManagerError, 
    UserAlreadyExistsError, 
    UserNotFoundError, 
    ConfigurationError,
    ValidationError
)

def bytes_to_human(byte_count: int) -> str:
    """Converts a byte count to a human-readable format (KB, MB, GB)."""
    if byte_count is None or not isinstance(byte_count, (int, float)):
        return "N/A"
    if byte_count == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while byte_count >= power and n < len(power_labels) -1 :
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}"

def get_install_settings() -> Dict[str, str]:
    # This function remains unchanged
    settings = {}
    print("--- Initial VPN Setup ---")
    
    try:
        public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        print(f"Detected Public IP: {public_ip}")
        settings["public_ip"] = input(f"Enter Public IP or press Enter to use detected IP [{public_ip}]: ").strip() or public_ip
    except Exception as e:
        print(f"Could not auto-detect public IP: {e}")
        settings["public_ip"] = input("Please enter the server's public IP address: ").strip()

    print("\n--- Certificate-based Authentication ---")
    settings["cert_port"] = input("Port [1194]: ").strip() or "1194"
    settings["cert_proto"] = input("Protocol (udp/tcp) [udp]: ").strip() or "udp"

    print("\n--- Username/Password-based Authentication ---")
    settings["login_port"] = input("Port [1195]: ").strip() or "1195"
    settings["login_proto"] = input("Protocol (udp/tcp) [udp]: ").strip() or "udp"

    print("\n--- DNS Configuration ---")
    print("1) System DNS\n2) Unbound (self-hosted)\n3) Cloudflare\n4) Google\n5) AdGuard DNS")
    dns_choice = ""
    while dns_choice not in ("1", "2", "3", "4", "5"):
        dns_choice = input("DNS [3]: ").strip() or "3"
    settings["dns"] = dns_choice

    print("\n--- Encryption Settings ---")
    settings["cipher"] = input("Cipher (e.g., AES-256-GCM) [AES-256-GCM]: ").strip() or "AES-256-GCM"
    settings["cert_size"] = input("Certificate Size (e.g., 2048) [2048]: ").strip() or "2048"

    return settings

def install_flow(openvpn_manager: OpenVPNManager) -> None:
    # This function remains unchanged
    if os.path.exists(OpenVPNManager.SETTINGS_FILE):
        print("Installation already detected. Aborting.")
        return

    raw_settings = get_install_settings()
    
    try:
        validated_settings = config.validate_install_settings(raw_settings)
        settings = raw_settings
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    print("\nStarting installation with the following settings:")
    for key, value in settings.items():
        print(f"  - {key}: {value}")
    
    confirm = input("Proceed with installation? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Installation aborted.")
        return

    try:
        openvpn_manager.install_openvpn(settings)
        _install_owpanel_command()

        print("From now on, you can run the panel from anywhere by typing: owpanel")
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)



def _install_owpanel_command() -> None:
    """Creates a system-wide command for the OpenVPN panel with proper permissions."""
    try:
        script_path = os.path.realpath(__file__)
        command_path = "/usr/local/bin/owpanel"
        os.chmod(script_path, 0o755)
        if os.path.lexists(command_path):
            os.remove(command_path)
        os.symlink(script_path, command_path)
        if os.path.exists(script_path):
            current_permissions = os.stat(script_path).st_mode
            if not (current_permissions & 0o111):
                os.chmod(script_path, 0o755)

    except Exception as e:
        print(f"⚠️  Warning: Could not create system-wide command. Error: {e}")

def print_management_menu() -> None:
    print("\n--- VPN Management Menu ---")
    print("👤 User Management:")
    print("  1. Add User")
    print("  2. Remove User")
    print("  3. List Users")
    print("  4. Get User Config")
    print("  5. Get Shared Config")
    print("\n📊 Traffic Management:")
    print("  6. Set User Quota")
    print("  7. View User Status")
    print("\n📦 System:")
    print("  8. System Backup")
    print("  9. System Restore")
    print("  10. Uninstall VPN")
    print("  11. Exit")

def add_user_flow(user_service: UserService) -> None:
    # This function remains unchanged
    while True:
        username = input("Enter username: ").strip()
        try:
            validated_username = config.validate_username(username)
            break
        except ValidationError as e:
            print(f"❌ {e}")
            continue
    password = getpass("Enter a password for the user (optional, press Enter to skip): ")

    try:
        config_data = user_service.create_user(validated_username, password or None)
        if config_data:
            config_path = os.path.join(os.path.expanduser("~"), f"{username}-cert.ovpn")
            with open(config_path, "w") as f:
                f.write(config_data)
            print(f"✅ Certificate-based config saved to: {config_path}")
            
        if password:
            shared_config = user_service.get_shared_config()
            shared_path = os.path.join(os.path.expanduser("~"), "shared-login.ovpn")
            with open(shared_path, "w") as f:
                f.write(shared_config)
            print(f"✅ Login-based config is available at: {shared_path}")
            
    except UserAlreadyExistsError as e:
        print(f"❌ {e}")
    except (ValidationError, VPNManagerError, Exception) as e:
        print(f"❌ Unexpected error creating user: {e}")

def remove_user_flow(user_service: UserService) -> None:
    # This function remains unchanged
    username = input("Enter username to remove: ").strip()
    try:
        user_service.remove_user(username)
    except UserNotFoundError as e:
        print(f"❌ {e}")
    except (VPNManagerError, Exception) as e:
        print(f"❌ Unexpected error removing user: {e}")

def list_users_flow(user_service: UserService) -> None:
    try:
        users = user_service.get_all_users_with_status()
        if not users:
            print("No users found.")
            return

        print("\n" + "-"*75)
        print(f"{'Username':<20} {'Status':<10} {'Quota':<12} {'Used':<12} {'Usage %':<10} {'Auth Types'}")
        print("-" * 75)

        user_map = {}
        for user in users:
            username = user['username']
            if username not in user_map:
                user_map[username] = {
                    'status': user.get('status', 'active'),
                    'quota_bytes': user.get('quota_bytes', 0),
                    'bytes_used': user.get('bytes_used', 0),
                    'auth_types': []
                }
            if user.get('auth_type'):
                user_map[username]['auth_types'].append(user['auth_type'])

        for username, data in user_map.items():
            quota = data['quota_bytes']
            used = data['bytes_used']
            
            usage_str = f"{((used/quota)*100):.1f}%" if quota else "N/A"
            auth_str = ", ".join(data['auth_types'])

            print(f"{username:<20} {data['status']:<10} {bytes_to_human(quota):<12} {bytes_to_human(used):<12} {usage_str:<10} {auth_str}")
        print("-" * 75)

    except Exception as e:
        print(f"❌ Error listing users: {e}")

def get_user_config_flow(user_service: UserService) -> None:
    # This function remains unchanged
    username = input("Enter username to get config for: ").strip()
    try:
        config = user_service.get_user_config(username)
        if config:
            print("\n--- User Config ---")
            print(config)
        else:
            print("User or config not found.")
    except Exception as e:
        print(f"❌ Error retrieving config: {e}")

def get_shared_config_flow(openvpn_manager: OpenVPNManager) -> None:
    # This function remains unchanged
    try:
        config = openvpn_manager.get_shared_config()
        print("\n--- Shared Login-Based Config ---")
        print(config)
        save_choice = input("\nSave this config to a file? (y/n) [n]: ").strip().lower()
        if save_choice == 'y':
            config_path = os.path.join(os.path.expanduser("~"), "shared-login.ovpn")
            with open(config_path, "w") as f:
                f.write(config)
            print(f"✅ Shared login config saved to: {config_path}")
    except Exception as e:
        print(f"❌ Error retrieving shared config: {e}")

# --- New Flows for Quota Management ---

def set_user_quota_flow(user_service: UserService) -> None:
    """Flow to set a data quota for a user."""
    username = input("Enter username to set quota for: ").strip()
    try:
        quota_gb_str = input(f"Enter quota for '{username}' in GB (e.g., 10). Enter 0 for unlimited: ").strip()
        quota_gb = float(quota_gb_str)
        if quota_gb < 0:
            print("❌ Quota cannot be negative.")
            return
            
        user_service.set_quota_for_user(username, quota_gb)
        
    except ValueError:
        print("❌ Invalid input. Please enter a number (e.g., 10, 2.5, or 0).")
    except UserNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def view_user_status_flow(user_service: UserService) -> None:
    """Flow to view the detailed traffic status of a user."""
    username = input("Enter username to view status for: ").strip()
    try:
        status = user_service.get_user_status(username)
        if not status:
            print("Could not retrieve status for this user.")
            return

        quota = status.get('quota_bytes', 0)
        used = status.get('bytes_used', 0)
        
        print(f"\n--- Status for {status['username']} ---")
        print(f"  Quota Limit: {bytes_to_human(quota)} ({'Unlimited' if quota == 0 else f'{quota:,} bytes'})")
        print(f"  Data Used:   {bytes_to_human(used)} ({used:,} bytes)")

        if quota > 0:
            percentage = (used / quota) * 100
            remaining_bytes = quota - used
            print(f"  Usage:       {percentage:.2f}%")
            print(f"  Remaining:   {bytes_to_human(remaining_bytes)}")
        
    except UserNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


def backup_flow(backup_service: BackupService) -> None:
    # This function remains unchanged
    try:
        password = getpass("Enter a password to encrypt the backup: ")
        if not password:
            print("Password cannot be empty. Backup cancelled.")
            return
        
        backup_dir = input("Enter backup directory path [~/]: ").strip() or "~/"
        backup_file = backup_service.create_backup(password, backup_dir)
        print(f"Backup created at: {backup_file}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

def restore_flow(backup_service: BackupService) -> None:
    # This function remains unchanged
    backup_path = input("Enter path to the backup file (local path or URL): ").strip()
    if not backup_path:
        print("Backup path cannot be empty. Restore cancelled.")
        return

    local_path = backup_path
    if backup_path.startswith(('http://', 'https://')):
        try:
            print(f"Downloading backup from {backup_path}...")
            local_path = os.path.join("/tmp", os.path.basename(backup_path))
            urllib.request.urlretrieve(backup_path, local_path)
            print(f"Download complete. Saved to {local_path}")
        except Exception as e:
            print(f"❌ Failed to download backup file: {e}")
            return

    password = getpass("Enter the password for the backup file: ")
    try:
        backup_service.restore_system(local_path, password)
        print("✅ System restore completed successfully.")
    except ValueError as e:
        print(f"❌ Restore failed: {e}")
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        sys.exit(1)
    finally:
        if backup_path.startswith(('http://', 'https://')) and os.path.exists(local_path):
            os.remove(local_path)

def uninstall_flow(openvpn_manager: OpenVPNManager) -> None:
    # This function remains unchanged
    confirm = input("This will completely remove OpenVPN. Are you sure? (Y/n): ").strip().lower()
    if confirm in ('', 'y', 'yes'):
        try:
            print("🗑️  Uninstalling OpenVPN...")
            
            db = Database()
            user_repo = UserRepository(db)
            login_manager = LoginUserManager()
            user_service = UserService(user_repo, openvpn_manager, login_manager)
            
            # Use get_all_users_with_status to get all users
            users = user_service.get_all_users_with_status()
            if users:
                unique_users = set(user['username'] for user in users)
                print(f"   └── Removing {len(unique_users)} VPN users...")
                for username in unique_users:
                    user_service.remove_user(username, silent=True)
            
            print("   └── Stopping services and cleaning up...")
            openvpn_manager.uninstall_openvpn(silent=True)
            print("✅ OpenVPN completely removed")
            
            sys.exit(0)
        except Exception as e:
            print(f"❌ Uninstallation failed: {e}")

def main() -> None:
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    
    db = Database()
    user_repo = UserRepository(db)
    login_manager = LoginUserManager()
    openvpn_manager = OpenVPNManager()
    user_service = UserService(user_repo, openvpn_manager, login_manager)
    backupable_components = [openvpn_manager, login_manager, user_service]
    backup_service = BackupService(backupable_components)

    if not os.path.exists(OpenVPNManager.SETTINGS_FILE):
        print("Welcome! It looks like this is a fresh installation.")
        install_flow(openvpn_manager)
        if not os.path.exists(OpenVPNManager.SETTINGS_FILE):
             sys.exit(0)

    while True:
        print_management_menu()
        choice = input("Enter your choice: ").strip()
        
        if choice == '1':
            add_user_flow(user_service)
        elif choice == '2':
            remove_user_flow(user_service)
        elif choice == '3':
            list_users_flow(user_service)
        elif choice == '4':
            get_user_config_flow(user_service)
        elif choice == '5':
            get_shared_config_flow(openvpn_manager)
        elif choice == '6':
            set_user_quota_flow(user_service)
        elif choice == '7':
            view_user_status_flow(user_service)
        elif choice == '8':
            backup_flow(backup_service)
        elif choice == '9':
            restore_flow(backup_service)
        elif choice == '10':
            uninstall_flow(openvpn_manager)
        elif choice == '11':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
