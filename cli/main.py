#!/usr/bin/env python3
import os
import sys
import re
from getpass import getpass
import urllib.request

real_script_path = os.path.realpath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(real_script_path), '..'))
os.chdir(project_root)
sys.path.insert(0, project_root)

from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from service.user_service import UserService
from data.user_repository import UserRepository
from data.db import Database
from core.backup_service import BackupService

def get_install_settings():
    """
    Interactively gathers all necessary settings for the initial installation.
    """
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

def install_flow(openvpn_manager: OpenVPNManager):
    """
    Orchestrates the entire installation process.
    """
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
        openvpn_manager.install_openvpn(settings)
        _patch_login_manager_file()
        _install_owpanel_command()
        print("\n✅ Installation completed successfully!")
        print("You can now manage users from the main menu.")
        print("From now on, you can run the panel from anywhere by typing: owpanel")
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)

def _patch_login_manager_file():
    """
    Acts as a self-healing mechanism to definitively fix the user creation bug.
    """
    print("▶️  Applying critical patch for user authentication...")
    file_path = os.path.join(project_root, 'core', 'login_user_manager.py')
    
    try:
        content = ""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
        else:
            print(f"⚠️  Warning: Could not find login_user_manager.py at {file_path}. Cannot apply patch.")
            return

        buggy_pattern = re.compile(r'input=f"\{username\}:\{password\}",\s*text=True,', re.DOTALL)
        correct_code = "input=f\"{username}:{password}\".encode('utf-8'),"
        
        if buggy_pattern.search(content):
            content = buggy_pattern.sub(correct_code, content)
            with open(file_path, 'w') as f:
                f.write(content)
            print("✅ Patch applied successfully.")
        else:
            print("✅ Authentication module is already up-to-date.")

    except Exception as e:
        print(f"⚠️  Warning: Could not apply patch. User creation might fail. Error: {e}")

def _install_owpanel_command():
    """
    Makes the script a system-wide command.
    """
    print("▶️  Registering 'owpanel' command...")
    try:
        script_path = os.path.realpath(__file__)
        command_path = "/usr/local/bin/owpanel"
        
        os.chmod(script_path, 0o755)
        
        if os.path.lexists(command_path):
            os.remove(command_path)
        os.symlink(script_path, command_path)
        print("✅ 'owpanel' command registered successfully.")
    except Exception as e:
        print(f"⚠️  Warning: Could not create system-wide command. Error: {e}")

def print_management_menu():
    print("\n--- VPN Management Menu (Dual Authentication) ---")
    print("1. Add a new user (Certificate + Optional Password)")
    print("2. Remove an existing user")
    print("3. List all users")
    print("4. Get user's certificate-based config")
    print("5. Get shared login-based config")
    print("6. System Backup")
    print("7. System Restore")
    print("8. Uninstall VPN")
    print("9. Exit")

def add_user_flow(user_service: UserService):
    username_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,31}$")

    while True:
        username = input("Enter username: ").strip()
        if not username_pattern.match(username):
            print("❌ Invalid username.")
            continue
        if user_service.user_repo.get_user_by_username(username):
            print(f"❌ User '{username}' already exists.")
            continue
        break

    print(f"\n📜 Certificate-based authentication will be enabled for '{username}'")
    create_login = input(f"🔐 Also enable password login for '{username}'? (y/n) [y]: ").strip().lower()
    create_login = create_login if create_login else 'y'
    
    password = None
    if create_login == 'y':
        password = getpass("Enter a password for the user: ")

    try:
        config_data = user_service.create_user(username, password)
        if config_data:
            config_path = os.path.join(os.path.expanduser("~"), f"{username}-cert.ovpn")
            with open(config_path, "w") as f:
                f.write(config_data)
            print(f"✅ Certificate-based config saved to: {config_path}")
            
        if password:
            shared_config = user_service.get_shared_config()
            shared_path = os.path.join(os.path.expanduser("~"), f"{username}-login.ovpn")
            with open(shared_path, "w") as f:
                f.write(shared_config)
            print(f"✅ Login-based config saved to: {shared_path}")
            
        print(f"\n🎉 User '{username}' now has dual authentication access:")
        print(f"   📜 Certificate-based: Use {username}-cert.ovpn")
        if password:
            print(f"   🔐 Username/Password: Use {username}-login.ovpn with username '{username}' and password")
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")

def remove_user_flow(user_service: UserService):
    username = input("Enter username to remove: ").strip()
    try:
        user_service.remove_user(username)
    except Exception as e:
        print(f"❌ Error removing user: {e}")

def list_users_flow(user_service: UserService):
    try:
        users = user_service.get_all_users()
        if not users:
            print("No users found.")
            return
        print("\n--- User List (Dual Authentication Support) ---")
        user_map = {}
        for user in users:
            username = user['username']
            if username not in user_map:
                user_map[username] = {
                    'username': username,
                    'auth_types': [],
                    'status': user.get('status', 'active'),
                    'created_at': user.get('created_at', 'Unknown')
                }
            if user.get('auth_type'):
                user_map[username]['auth_types'].append(user['auth_type'])
        
        print("📜 = Certificate-based | 🔐 = Username/Password")
        print("-" * 50)
        for username, info in user_map.items():
            auth_icons = []
            if 'certificate' in info['auth_types']:
                auth_icons.append('📜')
            if 'login' in info['auth_types']:
                auth_icons.append('🔐')
            
            status_icon = "✅" if info['status'] == 'active' else "❌"
            print(f"{status_icon} {username} {' '.join(auth_icons)} ({', '.join(info['auth_types']) if info['auth_types'] else 'No protocols'})")

    except Exception as e:
        print(f"❌ Error listing users: {e}")

def get_user_config_flow(user_service: UserService):
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

def get_shared_config_flow(openvpn_manager: OpenVPNManager):
    try:
        config = openvpn_manager.get_shared_config()
        print("\n--- Shared Login-Based Config ---")
        print("This config can be used by any user with login credentials")
        print("Users connect with their username and password")
        print("-" * 60)
        print(config)
        print("-" * 60)
        
        save_choice = input("\nSave this config to a file? (y/n) [n]: ").strip().lower()
        if save_choice == 'y':
            config_path = os.path.join(os.path.expanduser("~"), "shared-login.ovpn")
            with open(config_path, "w") as f:
                f.write(config)
            print(f"✅ Shared login config saved to: {config_path}")
            
    except Exception as e:
        print(f"❌ Error retrieving shared config: {e}")

def backup_flow(backup_service: BackupService):
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
    confirm = input("This will completely remove OpenVPN. Are you sure? (y/n): ").strip().lower()
    if confirm == 'y':
        try:
            openvpn_manager.uninstall_openvpn()
            print("✅ Uninstallation completed successfully. Exiting now.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Uninstallation failed: {e}")

def main():
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
            backup_flow(backup_service)
        elif choice == '7':
            restore_flow(backup_service)
        elif choice == '8':
            uninstall_flow(openvpn_manager)
        elif choice == '9':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
