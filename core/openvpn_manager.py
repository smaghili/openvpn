import os
import subprocess
from .protocol_manager import ProtocolManager
from .backup_interface import IBackupable

# Constants for paths and file names
OPENVPN_DIR = "/etc/openvpn"
EASYRSA_DIR = os.path.join(OPENVPN_DIR, "easy-rsa")
PKI_DIR = os.path.join(EASYRSA_DIR, "pki")
CLIENTS_DIR = os.path.join(OPENVPN_DIR, "clients")
SERVER_NAME = "server"
IPTABLES_DIR = "/etc/iptables"
ADD_RULES_SH = os.path.join(IPTABLES_DIR, "add-openvpn-rules.sh")
RM_RULES_SH = os.path.join(IPTABLES_DIR, "rm-openvpn-rules.sh")
PAM_CONF = "/etc/pam.d/openvpn"
SYSCTL_CONF = "/etc/sysctl.d/99-openvpn.conf"
DB_PATH = "vpn_manager.db"

class OpenVPNManager(ProtocolManager, IBackupable):
    """
    Manages the operational lifecycle of a dual-authentication OpenVPN setup.
    It is responsible for installation, user management, and providing backup assets.
    The backup/restore orchestration is handled by BackupService.
    """

    def __init__(self, protocol_repo):
        self.protocol_repo = protocol_repo
        self.settings = {}

    # --- IBackupable Interface Implementation ---

    def get_backup_assets(self) -> list[str]:
        """Returns the list of critical files and directories for OpenVPN."""
        return [OPENVPN_DIR, DB_PATH, IPTABLES_DIR, PAM_CONF, SYSCTL_CONF]

    def pre_restore(self):
        """Stops OpenVPN services before system files are replaced."""
        print("...Stopping OpenVPN services for restore...")
        subprocess.run(["systemctl", "stop", "openvpn@server-cert"], check=False)
        subprocess.run(["systemctl", "stop", "openvpn@server-login"], check=False)

    def post_restore(self):
        """Sets correct permissions and restarts services after restore."""
        print("...Finalizing OpenVPN restore...")
        if os.path.exists(PKI_DIR):
            subprocess.run(["chown", "-R", "root:root", OPENVPN_DIR], check=False)
            subprocess.run(["chmod", "700", os.path.join(PKI_DIR, "private")], check=False)
        self.start_openvpn_services()

    # --- Core Operational Methods ---

    def install_prerequisites(self):
        """Installs all necessary packages for OpenVPN and dependencies."""
        print("📦 Installing required packages...")
        packages = ["openvpn", "easy-rsa", "libpam-modules", "iptables", "gpg"]
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y"] + packages, check=True)

    def setup_pki(self):
        """Initializes the Public Key Infrastructure using EasyRSA."""
        print("🔑 Setting up Public Key Infrastructure (PKI)...")
        if not os.path.exists(EASYRSA_DIR):
            # This is a bit of a hack, easy-rsa needs a folder to run in.
            # A better solution would be to ship a copy of easy-rsa with the app.
            subprocess.run(["cp", "-r", "/usr/share/easy-rsa", EASYRSA_DIR], check=True)

        with open(os.path.join(EASYRSA_DIR, "vars"), "w") as f:
            f.write('set_var EASYRSA_REQ_CN "OpenVPN CA"\\n')
            f.write('set_var EASYRSA_BATCH "yes"\\n')

        commands = [
            "./easyrsa init-pki",
            "./easyrsa build-ca nopass",
            "./easyrsa gen-dh",
            f"./easyrsa build-server-full {SERVER_NAME} nopass",
            "./easyrsa build-client-full main nopass", # For shared login config
            "./easyrsa gen-crl"
        ]
        for cmd in commands:
            subprocess.run(cmd, shell=True, cwd=EASYRSA_DIR, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.run(["openvpn", "--genkey", "secret", os.path.join(PKI_DIR, "ta.key")], check=True)

    def generate_server_configs(self, settings):
        """Generates server-cert.conf and server-login.conf based on user settings."""
        print("📝 Generating server configuration files...")
        self.settings = settings
        self._generate_cert_server_config()
        self._generate_login_server_config()
        self._generate_shared_login_ovpn()

    def setup_firewall_rules(self, settings):
        """Creates and applies iptables firewall rules dynamically."""
        print("🔥 Setting up firewall rules...")
        self.settings = settings
        os.makedirs(IPTABLES_DIR, exist_ok=True)
        
        nic = settings['network_interface']
        add_rules = f"""#!/bin/sh
iptables -t nat -I POSTROUTING 1 -s 10.8.0.0/24 -o {nic} -j MASQUERADE
iptables -I INPUT 1 -i tun0 -j ACCEPT
iptables -I FORWARD 1 -i {nic} -o tun0 -j ACCEPT
iptables -I FORWARD 1 -i tun0 -o {nic} -j ACCEPT
iptables -I INPUT 1 -i {nic} -p {settings['cert_proto']} --dport {settings['cert_port']} -j ACCEPT
iptables -t nat -I POSTROUTING 1 -s 10.9.0.0/24 -o {nic} -j MASQUERADE
iptables -I INPUT 1 -i tun1 -j ACCEPT
iptables -I FORWARD 1 -i {nic} -o tun1 -j ACCEPT
iptables -I FORWARD 1 -i tun1 -o {nic} -j ACCEPT
iptables -I INPUT 1 -i {nic} -p {settings['login_proto']} --dport {settings['login_port']} -j ACCEPT
"""
        with open(ADD_RULES_SH, "w") as f: f.write(add_rules)
        os.chmod(ADD_RULES_SH, 0o755)
        subprocess.run([ADD_RULES_SH], check=True)

    def enable_ip_forwarding(self):
        """Enables IP forwarding in the kernel."""
        print("🛰️  Enabling IP forwarding...")
        content = "net.ipv4.ip_forward=1\\n"
        if self.settings.get("ipv6"):
            content += "net.ipv6.conf.all.forwarding=1\\n"
        with open(SYSCTL_CONF, "w") as f: f.write(content)
        subprocess.run(["sysctl", "-p", SYSCTL_CONF], check=True)

    def setup_pam(self):
        """Configures PAM for OpenVPN login authentication."""
        print("🔐 Configuring PAM for password authentication...")
        with open(PAM_CONF, "w") as f:
            f.write("auth    required    pam_unix.so shadow nodelay\\n")
            f.write("account required    pam_unix.so\\n")

    def start_openvpn_services(self):
        """Enables and starts the dual OpenVPN systemd services."""
        print("🚀 Starting OpenVPN services...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "openvpn@server-cert"], check=True)
        subprocess.run(["systemctl", "enable", "openvpn@server-login"], check=True)
        subprocess.run(["systemctl", "restart", "openvpn@server-cert"], check=True)
        subprocess.run(["systemctl", "restart", "openvpn@server-login"], check=True)

    def remove_openvpn(self):
        """Completely removes OpenVPN and all related files."""
        print("🔥 Removing OpenVPN...")
        if os.path.exists(ADD_RULES_SH):
            with open(ADD_RULES_SH, 'r') as f:
                rm_rules_content = f.read().replace('-I', '-D')
            with open(RM_RULES_SH, "w") as f: f.write(rm_rules_content)
            os.chmod(RM_RULES_SH, 0o755)
            subprocess.run([RM_RULES_SH], check=False)

        self.pre_restore()
        subprocess.run(["systemctl", "disable", "openvpn@server-cert"], check=False)
        subprocess.run(["systemctl", "disable", "openvpn@server-login"], check=False)
        
        for path in self.get_backup_assets():
            if os.path.exists(path):
                if os.path.isdir(path):
                    subprocess.run(["rm", "-rf", path], check=False)
                else:
                    os.remove(path)
        
        subprocess.run(["sysctl", "--system"], check=False)
        subprocess.run(["apt-get", "remove", "--purge", "-y", "openvpn"], check=False)
        print("✅ OpenVPN uninstalled.")

    def add_user(self, user):
        """Adds a certificate-based user and generates their .ovpn file."""
        self._generate_client_cert(user.username)
        self._generate_cert_ovpn(user.username)

    def remove_user(self, user):
        """Revokes a user's certificate and deletes their files."""
        self._revoke_client_cert(user.username)
        self._delete_client_files(user.username)

    def _generate_client_cert(self, username):
        subprocess.run(f"./easyrsa build-client-full {username} nopass", shell=True, cwd=EASYRSA_DIR, check=True, stdout=subprocess.DEVNULL)

    def _revoke_client_cert(self, username):
        subprocess.run(f'echo "yes" | ./easyrsa revoke {username}', shell=True, cwd=EASYRSA_DIR, check=True, stdout=subprocess.DEVNULL)
        subprocess.run("./easyrsa gen-crl", shell=True, cwd=EASYRSA_DIR, check=True, stdout=subprocess.DEVNULL)

    def _delete_client_files(self, username):
        client_file = os.path.join(CLIENTS_DIR, f"{username}-cert.ovpn")
        if os.path.exists(client_file):
            os.remove(client_file)

    def _get_base_config(self, settings):
        """Returns a base server configuration string."""
        cipher_map = {"1": "AES-128-GCM", "2": "AES-256-GCM", "3": "CHACHA20-POLY1305"}
        dns_lines = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.8.0.1"\\npush "dhcp-option DNS 10.9.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\\npush "dhcp-option DNS 94.140.15.15"'
        }
        
        config = f"""
ca {PKI_DIR}/ca.crt
cert {PKI_DIR}/issued/{SERVER_NAME}.crt
key {PKI_DIR}/private/{SERVER_NAME}.key
dh {PKI_DIR}/dh.pem
crl-verify {PKI_DIR}/crl.pem
tls-auth {PKI_DIR}/ta.key 0
keepalive 10 120
user nobody
group nogroup
persist-key
persist-tun
verb 3
explicit-exit-notify 1
cipher {cipher_map.get(settings.get("cipher", "1"))}
auth SHA256
{dns_lines[settings.get("dns", "1")]}
"""
        if settings.get("compression"):
            config += "compress lz4-v2\\npush \\"compress lz4-v2\\"\\n"
        if settings.get("ipv6"):
            config += """
server-ipv6 fd42:42:42:42::/112
tun-ipv6
push "route-ipv6 2000::/3"
push "redirect-gateway ipv6"
"""
        return config

    def _generate_cert_server_config(self):
        """Generates the server config for certificate-based auth."""
        base_config = self._get_base_config(self.settings)
        cert_config = f"""
port {self.settings['cert_port']}
proto {self.settings['cert_proto']}
dev tun0
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist /etc/openvpn/ipp-cert.txt
push "redirect-gateway def1 bypass-dhcp"
status /var/log/openvpn/status-cert.log
{base_config}
"""
        with open(f"{OPENVPN_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config.strip())

    def _generate_login_server_config(self):
        """Generates the server config for login-based auth."""
        base_config = self._get_base_config(self.settings)
        login_config = f"""
port {self.settings['login_port']}
proto {self.settings['login_proto']}
dev tun1
server 10.9.0.0 255.255.255.0
ifconfig-pool-persist /etc/openvpn/ipp-login.txt
push "redirect-gateway def1 bypass-dhcp"
status /var/log/openvpn/status-login.log
plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn
client-cert-not-required
username-as-common-name
{base_config}
"""
        with open(f"{OPENVPN_DIR}/server-login.conf", "w") as f:
            f.write(login_config.strip())

    def _generate_cert_ovpn(self, username):
        """Generates a .ovpn file for a certificate user."""
        client_config = self._get_base_client_config(self.settings['cert_proto'], self.settings['server_ip'], self.settings['cert_port'])
        
        with open(f"{PKI_DIR}/ca.crt", "r") as f: ca_pem = f.read()
        with open(f"{PKI_DIR}/issued/{username}.crt", "r") as f: cert_pem = f.read()
        with open(f"{PKI_DIR}/private/{username}.key", "r") as f: key_pem = f.read()
        with open(f"{PKI_DIR}/ta.key", "r") as f: ta_key = f.read()

        full_config = f"""
{client_config}
<ca>
{ca_pem}
</ca>
<cert>
{cert_pem}
</cert>
<key>
{key_pem}
</key>
<tls-auth>
{ta_key}
</tls-auth>
"""
        os.makedirs(CLIENTS_DIR, exist_ok=True)
        with open(os.path.join(CLIENTS_DIR, f"{username}-cert.ovpn"), "w") as f:
            f.write(full_config.strip())

    def _generate_shared_login_ovpn(self):
        """Generates the shared login.ovpn file."""
        client_config = self._get_base_client_config(self.settings['login_proto'], self.settings['server_ip'], self.settings['login_port'])
        client_config += "auth-user-pass\\n"

        with open(f"{PKI_DIR}/ca.crt", "r") as f: ca_pem = f.read()
        with open(f"{PKI_DIR}/issued/main.crt", "r") as f: cert_pem = f.read()
        with open(f"{PKI_DIR}/private/main.key", "r") as f: key_pem = f.read()
        with open(f"{PKI_DIR}/ta.key", "r") as f: ta_key = f.read()

        full_config = f"""
{client_config}
<ca>
{ca_pem}
</ca>
<cert>
{cert_pem}
</cert>
<key>
{key_pem}
</key>
<tls-auth>
{ta_key}
</tls-auth>
"""
        os.makedirs(CLIENTS_DIR, exist_ok=True)
        with open(os.path.join(CLIENTS_DIR, "login.ovpn"), "w") as f:
            f.write(full_config.strip())

    def _get_base_client_config(self, proto, ip, port):
        """Returns a base .ovpn configuration string."""
        return f"""
client
dev tun
proto {proto}
remote {ip} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verb 3
key-direction 1
""".strip() + "\\n"
