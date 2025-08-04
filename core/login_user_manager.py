import os
import hashlib
import subprocess

LOGIN_USERS_FILE = "/etc/openvpn/login-users.txt"
CLIENTS_DIR = "/etc/openvpn/clients"
SERVER_LOGIN_CONF = "/etc/openvpn/server-login.conf"

class LoginUserManager:
    """
    Manages OpenVPN login-based users (username/password) and generates client configs.
    Stores users in a secure file and generates .ovpn files for each user.
    Also manages the login-based OpenVPN server configuration and service.
    """
    def __init__(self):
        os.makedirs(CLIENTS_DIR, exist_ok=True)
        if not os.path.isfile(LOGIN_USERS_FILE):
            os.makedirs(os.path.dirname(LOGIN_USERS_FILE), exist_ok=True)
            with open(LOGIN_USERS_FILE, "w"):
                pass
        self.setup_login_server()

    def add_user(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with open(LOGIN_USERS_FILE, "a") as f:
            f.write(f"{username}:{password_hash}\n")
        self.generate_client_config(username)

    def remove_user(self, username):
        if os.path.isfile(LOGIN_USERS_FILE):
            with open(LOGIN_USERS_FILE, "r") as f:
                lines = f.readlines()
            with open(LOGIN_USERS_FILE, "w") as f:
                for line in lines:
                    if not line.startswith(f"{username}:"):
                        f.write(line)
        ovpn_path = os.path.join(CLIENTS_DIR, f"{username}-login.ovpn")
        if os.path.isfile(ovpn_path):
            os.remove(ovpn_path)

    def generate_client_config(self, username):
        ovpn_path = os.path.join(CLIENTS_DIR, f"{username}-login.ovpn")
        with open(ovpn_path, "w") as f:
            f.write(
                """client\ndev tun\nproto udp\nremote YOUR_SERVER_IP 1195\nresolv-retry infinite\nnobind\npersist-key\npersist-tun\nauth-user-pass\nremote-cert-tls server\nverb 3\n"""
            )
        return ovpn_path

    def generate_server_config(self, config):
        conf_path = "/etc/openvpn/server-login.conf"
        cipher_map = {"1": "AES-128-GCM", "2": "AES-256-GCM", "3": "CHACHA20-POLY1305"}
        dns_lines = {
            "1": "# Use system DNS (handled by OS)",
            "2": "push \"dhcp-option DNS 10.9.0.1\"",
            "3": "push \"dhcp-option DNS 1.1.1.1\"",
            "4": "push \"dhcp-option DNS 8.8.8.8\""
        }
        cipher = cipher_map.get(config.get("cipher", "1"), "AES-128-GCM")
        compression = config.get("compression", False)
        ipv6 = config.get("ipv6", False)
        dns = config.get("dns", "1")
        with open(conf_path, "w") as f:
            f.write(f"port 1195\n")
            f.write(f"proto udp\n")
            f.write(f"dev tun1\n")
            f.write(f"ca /etc/openvpn/easy-rsa/pki/ca.crt\n")
            f.write(f"cert /etc/openvpn/easy-rsa/pki/issued/server.crt\n")
            f.write(f"key /etc/openvpn/easy-rsa/pki/private/server.key\n")
            f.write(f"dh /etc/openvpn/easy-rsa/pki/dh.pem\n")
            f.write(f"server 10.9.0.0 255.255.255.0\n")
            f.write(f"ifconfig-pool-persist ipp-login.txt\n")
            f.write(f"plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn\n")
            f.write(f"username-as-common-name\n")
            f.write(f"verify-client-cert none\n")
            f.write(f"client-cert-not-required\n")
            f.write(f"auth-user-pass-verify {LOGIN_USERS_FILE} via-file\n")
            f.write(f"{dns_lines[dns]}\n")
            f.write(f"push \"redirect-gateway def1 bypass-dhcp\"\n")
            f.write(f"keepalive 10 120\n")
            f.write(f"crl-verify /etc/openvpn/easy-rsa/pki/crl.pem\n")
            f.write(f"tls-server\n")
            f.write(f"tls-version-min 1.2\n")
            f.write(f"cipher {cipher}\n")
            f.write(f"auth SHA256\n")
            if compression:
                f.write(f"compress lz4-v2\n")
            if ipv6:
                f.write(f"server-ipv6 fd42:42:42:42::/112\n")
                f.write(f"tun-ipv6\n")
                f.write(f"push \"route-ipv6 2000::/3\"\n")
                f.write(f"push \"redirect-gateway ipv6\"\n")
            f.write(f"status /var/log/openvpn/status-login.log\n")
            f.write(f"verb 3\n")

    def setup_login_server(self):
        os.makedirs("/etc/openvpn", exist_ok=True)
        # تولید فایل پیکربندی سرور login-based
        if not os.path.isfile(SERVER_LOGIN_CONF):
            with open(SERVER_LOGIN_CONF, "w") as f:
                f.write(
                    """port 1195\n"
                    "proto udp\n"
                    "dev tun1\n"
                    "ca /etc/openvpn/easy-rsa/pki/ca.crt\n"
                    "cert /etc/openvpn/easy-rsa/pki/issued/server.crt\n"
                    "key /etc/openvpn/easy-rsa/pki/private/server.key\n"
                    "dh /etc/openvpn/easy-rsa/pki/dh.pem\n"
                    "server 10.9.0.0 255.255.255.0\n"
                    "ifconfig-pool-persist ipp-login.txt\n"
                    "plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn\n"
                    "username-as-common-name\n"
                    "verify-client-cert none\n"
                    "client-cert-not-required\n"
                    f"auth-user-pass-verify {LOGIN_USERS_FILE} via-file\n"
                    "push \"redirect-gateway def1 bypass-dhcp\"\n"
                    "keepalive 10 120\n"
                    "crl-verify /etc/openvpn/easy-rsa/pki/crl.pem\n"
                    "tls-server\n"
                    "tls-version-min 1.2\n"
                    "cipher AES-128-GCM\n"
                    "auth SHA256\n"
                    "status /var/log/openvpn/status-login.log\n"
                    "verb 3\n"
                )
        # راه‌اندازی سرویس systemd مجزا
        subprocess.run(["sudo", "systemctl", "enable", "openvpn@server-login"], check=False)
        subprocess.run(["sudo", "systemctl", "restart", "openvpn@server-login"], check=False)