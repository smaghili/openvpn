#!/usr/bin/env python3
import os
import sys
import re
from getpass import getpass
import urllib.request

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(project_root)
sys.path.insert(0, project_root)

from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from service.user_service import UserService
from data.user_repository import UserRepository
from data.db import Database
from core.backup_service import BackupService

# --- Installation Flow ---
def get_install_settings():
    """
    Interactively gathers all necessary settings for the initial installation.
    This function is designed to be self-contained and easy to understand.
    """
    settings = {}
    print("--- Initial VPN Setup ---")
    
    # 1. Detect public IP
    try:
        public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        print(f"Detected Public IP: {public_ip}")
        settings["public_ip"] = input(f"Enter Public IP or press Enter to use detected IP [{public_ip}]: ").strip() or public_ip
    except Exception as e:
        print(f"Could not auto-detect public IP: {e}")
        settings["public_ip"] = input("Please enter the server's public IP address: ").strip()

    # 2. Ports and Protocol for Certificate-based Auth
    print("\n--- Certificate-based Authentication ---")
    settings["cert_port"] = input("Port [1194]: ").strip() or "1194"
    settings["cert_proto"] = input("Protocol (udp/tcp) [udp]: ").strip() or "udp"

    # 3. Ports and Protocol for Login-based Auth
    print("\n--- Username/Password-based Authentication ---")
    settings["login_port"] = input("Port [1195]: ").strip() or "1195"
    settings["login_proto"] = input("Protocol (udp/tcp) [udp]: ").strip() or "udp"

    # 4. DNS Configuration
    print("\n--- DNS Configuration ---")
    print("1) System DNS\n2) Unbound (self-hosted)\n3) Cloudflare\n4) Google\n5) AdGuard DNS")
    dns_choice = ""
    while dns_choice not in ("1", "2", "3", "4", "5"):
        dns_choice = input("DNS [3]: ").strip() or "3"
    settings["dns"] = dns_choice

    # 5. Encryption Settings
    print("\n--- Encryption Settings ---")
    settings["cipher"] = input("Cipher (e.g., AES-256-GCM) [AES-256-GCM]: ").strip() or "AES-256-GCM"
    settings["cert_size"] = input("Certificate Size (e.g., 2048) [2048]: ").strip() or "2048"

    return settings

def install_flow(openvpn_manager: OpenVPNManager):
    """Orchestrates the entire installation process."""
    # The check for installation is now based on the existence of the settings file.
    if os.path.exists(OpenVPNManager.SETTINGS_FILE):
        print("Installation already detected. Aborting.")
        return

    settings = get_install_settings()
    
    print("\nStarting installation with the following settings:")
    for key, value in settings.items():
        print(f"  - {key}: {value}")
    
    confirm = input("Proceed with installation? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Installation aborted.")
        return

    try:
        # Pass the entire settings dictionary to the manager
        openvpn_manager.install_openvpn(settings)
        _install_owpanel_command()
        print("\n✅ Installation completed successfully!")
        print("You can now manage users from the main menu.")
        print("From now on, you can run the panel from anywhere by typing: owpanel")
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)


def _install_owpanel_command():
    """Makes the script a system-wide command."""
    print("▶️  Registering 'owpanel' command...")
    try:
        # Get the absolute path to the currently running script (main.py)
        script_path = os.path.abspath(__file__)
        command_path = "/usr/local/bin/owpanel"
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Create a symbolic link, overwriting if it exists
        if os.path.exists(command_path):
            os.remove(command_path)
        os.symlink(script_path, command_path)
        print("✅ 'owpanel' command registered successfully.")
    except Exception as e:
        print(f"⚠️  Warning: Could not create system-wide command. You may need to run the panel using 'python3 -m cli.main'. Error: {e}")



# --- Management Menu Flows ---
def print_management_menu():
    """Prints the main management menu."""
    print("\n--- VPN Management Menu ---")
    print("1. Add a new user")
    print("2. Remove an existing user")
    print("3. List all users")
    print("4. Get a user's config file")
    print("5. System Backup")
    print("6. System Restore")
    print("7. Uninstall VPN")
    print("8. Get shared config")
    print("9. Exit")

def add_user_flow(user_service: UserService):
    """Handles the 'add user' workflow with robust input validation."""
    # Regex for a valid system/certificate username.
    username_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,31}$")

    while True:
        username = input("Enter username: ").strip()
        if not username_pattern.match(username):
            print("❌ Invalid username. It must start with a letter and contain only letters, numbers, hyphens, or underscores (2-32 characters).")
            continue

        if user_service.user_repo.get_user_by_username(username):
            print(f"❌ User '{username}' already exists. Please choose a different name.")
            continue
        
        break

    create_login = input(f"Enable password login for '{username}'? (y/n) [n]: ").strip().lower()
    password = None
    if create_login == 'y':
        password = getpass("Enter a password for the user: ")

    try:
        config_data = user_service.create_user(username, password)
        if config_data:
            config_path = os.path.join(os.path.expanduser("~"), f"{username}.ovpn")
            with open(config_path, "w") as f:
                f.write(config_data)
            print(f"✅ User config saved to: {config_path}")
    except Exception as e:
        print(f"❌ Error creating user: {e}")

def remove_user_flow(user_service: UserService):
    """Handles the 'remove user' workflow."""
    username = input("Enter username to remove: ").strip()
    try:
        user_service.remove_user(username)
    except Exception as e:
        print(f"❌ Error removing user: {e}")

def list_users_flow(user_service: UserService):
    """Handles the 'list users' workflow."""
    try:
        users = user_service.get_all_users()
        if not users:
            print("No users found.")
            return
        print("\n--- User List ---")
        user_map = {}
        for user in users:
            if user['username'] not in user_map:
                user_map[user['username']] = []
            user_map[user['username']].append(user['auth_type'])
        
        for username, auth_types in user_map.items():
            print(f"- {username} ({', '.join(auth_types)})")

    except Exception as e:
        print(f"❌ Error listing users: {e}")

def get_user_config_flow(user_service: UserService):
    """Handles the 'get user config' workflow."""
    username = input("Enter username to get config for: ").strip()
    try:
        config = user_service.get_user_config(username)
        if config:
            print("\n--- User Config ---")
            print(config)
        else:
            print("User or config not found (note: only cert-based users have configs).")
    except Exception as e:
        print(f"❌ Error retrieving config: {e}")

def get_shared_config_flow(openvpn_manager: OpenVPNManager):
    """Handles the 'get shared config' workflow."""
    try:
        config = openvpn_manager.get_shared_config()
        print("\n--- Shared Config ---")
        print(config)
    except Exception as e:
        print(f"❌ Error retrieving shared config: {e}")

def backup_flow(backup_service: BackupService):
    """Handles the system backup workflow."""
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

def restore_flow(backup_service: BackupService):
    """Handles the system restore workflow."""
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

def uninstall_flow(openvpn_manager: OpenVPNManager):
    """
    Handles the uninstallation workflow and exits the application upon success.
    """
    confirm = input("This will completely remove OpenVPN and all related configurations. Are you sure? (y/n): ").strip().lower()
    if confirm == 'y':
        try:
            openvpn_manager.uninstall_openvpn()
            print("✅ Uninstallation completed successfully. Exiting now.")
            sys.exit(0) # Exit the application after successful uninstall
        except Exception as e:
            print(f"❌ Uninstallation failed: {e}")

# --- Main Application Logic ---
def main():
    """Main entry point of the application."""
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    
    # --- Dependency Injection Setup ---
    db = Database()
    user_repo = UserRepository(db)
    login_manager = LoginUserManager()
    # OpenVPNManager now loads its state upon initialization
    openvpn_manager = OpenVPNManager()
    
    user_service = UserService(user_repo, openvpn_manager, login_manager)
    
    backupable_components = [openvpn_manager, login_manager, user_service]
    backup_service = BackupService(backupable_components)

    # --- Application Flow ---
    # The single source of truth for installation status is the settings file.
    if not os.path.exists(OpenVPNManager.SETTINGS_FILE):
        print("Welcome! It looks like this is a fresh installation.")
        install_flow(openvpn_manager)
        if not os.path.exists(OpenVPNManager.SETTINGS_FILE):
             sys.exit(0) # Exit if installation was aborted or failed

    # Main management loop
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
            backup_flow(backup_service)
        elif choice == '6':
            restore_flow(backup_service)
        elif choice == '7':
            uninstall_flow(openvpn_manager)
        elif choice == '8':
            get_shared_config_flow(openvpn_manager)
        elif choice == '9':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
