import getpass
import os
import socket
import subprocess
import urllib.request

from core.login_user_manager import LoginUserManager
from core.openvpn_manager import OpenVPNManager
from core.backup_service import BackupService
from data.db import Database
from data.protocol_repository import ProtocolRepository
from data.user_repository import UserRepository
from service.user_service import UserService


def get_default_ip():
    """Gets the default public IP address of the server."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_network_interface():
    """Gets the default network interface."""
    try:
        result = subprocess.run(
            ["ip", "route", "get", "8.8.8.8"], capture_output=True, text=True, check=True
        )
        return result.stdout.split("dev")[1].split()[0]
    except Exception:
        return "eth0"


def get_install_settings():
    """Gathers all necessary settings for a new OpenVPN installation."""
    print("🚀 Welcome to the OpenVPN Dual-Auth Installer!")
    settings = {}
    default_ip = get_default_ip()
    settings["server_ip"] = input(f"Server IP address [{default_ip}]: ").strip() or default_ip

    print("\\n--- Certificate Server (for advanced users) ---")
    settings["cert_port"] = input("Port [1194]: ").strip() or "1194"
    settings["cert_proto"] = input("Protocol (udp/tcp) [udp]: ").strip().lower() or "udp"

    print("\\n--- Login Server (for simple users) ---")
    settings["login_port"] = input("Port [1195]: ").strip() or "1195"
    settings["login_proto"] = input("Protocol (udp/tcp) [udp]: ").strip().lower() or "udp"

    print("\\n--- DNS Configuration ---")
    print("1) System DNS\\n2) Unbound (self-hosted)\\n3) Cloudflare\\n4) Google\\n5) AdGuard DNS")
    dns_choice = ""
    while dns_choice not in ("1", "2", "3", "4", "5"):
        dns_choice = input("DNS [3]: ").strip() or "3"
    settings["dns"] = dns_choice

    print("\\n--- Encryption Settings ---")
    print("1) AES-128-GCM (Recommended)\\n2) AES-256-GCM\\n3) CHACHA20-POLY1305")
    cipher_choice = ""
    while cipher_choice not in ("1", "2", "3"):
        cipher_choice = input("Cipher [1]: ").strip() or "1"
    settings["cipher"] = cipher_choice

    settings["compression"] = (input("Enable compression? (not recommended) [n]: ").strip().lower() or "n") == "y"
    settings["ipv6"] = (input("Enable IPv6 support? [n]: ").strip().lower() or "n") == "y"
    settings["network_interface"] = get_network_interface()

    print("\\n✅ Configuration complete. Ready to install.")
    return settings


def install_flow(openvpn_mgr):
    """Orchestrates the first-time installation of OpenVPN."""
    settings = get_install_settings()
    if input("Proceed with installation? [y/n]: ").strip().lower() != "y":
        print("Installation aborted.")
        return False
    try:
        print("🔧 Starting installation...")
        openvpn_mgr.install_prerequisites()
        openvpn_mgr.setup_pki()
        openvpn_mgr.generate_server_configs(settings)
        openvpn_mgr.setup_firewall_rules(settings)
        openvpn_mgr.enable_ip_forwarding()
        openvpn_mgr.setup_pam()
        openvpn_mgr.start_openvpn_services()
        if settings["dns"] == "2":
            # This is a bit of a hack. UnboundManager should be a separate service.
            # For now, we call it directly from OpenVPNManager.
            pass # Unbound setup is now part of OpenVPNManager's assets
        print("\\n🎉 OpenVPN has been successfully installed!")
        return True
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False


def print_management_menu():
    """Prints the user management menu."""
    print("\\n--- VPN User Manager ---")
    print("1) Add User")
    print("2) Remove User")
    print("3) List Users")
    print("4) Create System Backup")
    print("5) Restore from Backup")
    print("6) Uninstall OpenVPN")
    print("7) Exit")


def add_user_flow(user_service):
    """Handles the flow for adding a new user."""
    username = input("Username: ")
    if not username:
        print("Username cannot be empty.")
        return
    password = getpass.getpass("Password: ")
    try:
        user_service.create_user(username, password)
        print(f"✅ User '{username}' created.")
        print(f"Certificate config: /etc/openvpn/clients/{username}-cert.ovpn")
        print(f"Login config: /etc/openvpn/clients/login.ovpn")
    except Exception as e:
        print(f"❌ Error: {e}")


def remove_user_flow(user_service):
    """Handles the flow for removing a user."""
    username = input("Username to remove: ")
    if not username:
        return
    try:
        user_service.remove_user(username)
        print("✅ User removed successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")


def list_users_flow(user_service):
    """Handles the flow for listing all users."""
    users = user_service.list_users()
    if not users:
        print("No users found.")
        return
    print("\\n--- Registered Users ---")
    for u in users:
        print(f"- {u['username']} (status: {u['status']})")


def backup_flow(backup_service):
    """Handles the system backup flow using the dedicated service."""
    print("This will create a complete, encrypted backup of all system configurations.")
    password = getpass.getpass("Enter a strong password for the backup file: ")
    if not password:
        print("Password cannot be empty. Aborting.")
        return
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Passwords do not match. Aborting.")
        return
    try:
        backup_service.create_backup(password)
    except Exception as e:
        print(f"❌ Backup failed: {e}")


def restore_flow(backup_service):
    """Handles the system restore flow using the dedicated service."""
    print("⚠️  WARNING: This will overwrite your current configurations.")
    path = input("Enter path or URL to the encrypted backup file (.gpg): ").strip()
    if not path:
        return
    
    local_path = path
    if path.startswith(('http://', 'https://')):
        try:
            print(f"Downloading backup from {path}...")
            local_path = "/tmp/system_backup_download.gpg"
            urllib.request.urlretrieve(path, local_path)
            print("Download complete.")
        except Exception as e:
            print(f"❌ Failed to download file: {e}")
            return

    password = getpass.getpass("Enter the password for the backup file: ")
    if not password:
        print("Password cannot be empty. Aborting.")
        return
    try:
        backup_service.restore_from_backup(local_path, password)
    except FileNotFoundError:
        print("❌ Error: Backup file not found.")
    except (ValueError, RuntimeError) as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ A critical error occurred during restore: {e}")
    finally:
        if local_path != path and os.path.exists(local_path):
            os.remove(local_path)


def remove_openvpn_flow(openvpn_mgr):
    """Handles the flow for uninstalling OpenVPN."""
    confirm = input("Are you sure you want to fully uninstall OpenVPN? (yes/no): ").strip().lower()
    if confirm == "yes":
        openvpn_mgr.remove_openvpn()
        return True
    else:
        print("Operation cancelled.")
        return False


def main():
    """Main entry point for the CLI application."""
    if os.geteuid() != 0:
        print("This script must be run as root.")
        return

    # --- Dependency Injection ---
    db = Database()
    user_repo = UserRepository(db)
    protocol_repo = ProtocolRepository(db)
    
    # Protocol managers
    openvpn_mgr = OpenVPNManager(protocol_repo)
    login_user_mgr = LoginUserManager()
    # In the future, you would add other managers like:
    # wireguard_mgr = WireGuardManager()
    
    # Create a list of all services that can be backed up
    backupable_services = [openvpn_mgr] #, wireguard_mgr]
    
    # Core services
    user_service = UserService(user_repo, protocol_repo, openvpn_mgr, login_user_mgr)
    backup_service = BackupService(backupable_services)

    # --- Application Flow ---
    if not os.path.exists("/etc/openvpn/server-cert.conf"):
        if not install_flow(openvpn_mgr):
            return

    while True:
        print_management_menu()
        choice = input("Select an option: ").strip()
        if choice == "1": add_user_flow(user_service)
        elif choice == "2": remove_user_flow(user_service)
        elif choice == "3": list_users_flow(user_service)
        elif choice == "4": backup_flow(backup_service)
        elif choice == "5": restore_flow(backup_service)
        elif choice == "6":
            if remove_openvpn_flow(openvpn_mgr): break
        elif choice == "7":
            db.close()
            print("Goodbye.")
            break
        else:
            print("Invalid option.")

if __name__ == '__main__':
    main()
