import os
import subprocess
import shutil
import json
from .backup_interface import IBackupable

class OpenVPNManager(IBackupable):
    """
    Manages the complete lifecycle of OpenVPN server instances, including installation,
    configuration, user management, and backup/restore operations.
    This class now persists its settings to a JSON file for stateful operation.
    """

    OPENVPN_DIR = "/etc/openvpn"
    SERVER_CONFIG_DIR = f"{OPENVPN_DIR}/server"
    EASYRSA_DIR = f"{OPENVPN_DIR}/easy-rsa"
    PKI_DIR = f"{EASYRSA_DIR}/pki"
    FIREWALL_RULES_V4 = "/etc/iptables/rules.v4"
    SETTINGS_FILE = f"{OPENVPN_DIR}/settings.json"
    
    def __init__(self):
        self.settings = {}
        self._load_settings()

    def _load_settings(self):
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Warning: Could not load settings file: {e}")

    def _save_settings(self):
        os.makedirs(self.OPENVPN_DIR, exist_ok=True)
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def install_openvpn(self, settings: dict):
        print("▶️  Starting OpenVPN installation...")
        self.settings = settings
        
        self._install_prerequisites()
        self._setup_pki()
        self._generate_server_configs()
        self._setup_firewall_rules()
        self._enable_ip_forwarding()
        self._setup_pam()
        if self.settings.get("dns") == "2":
            self._setup_unbound()
        self._start_openvpn_services()
        
        self._save_settings()
        print("✅ OpenVPN installation phase completed and settings saved.")

    def _install_prerequisites(self):
        print("[1/7] Installing prerequisites...")
        packages = ["openvpn", "easy-rsa", "iptables-persistent", "openssl", "ca-certificates", "curl", "libpam-pwquality"]
        if self.settings.get("dns") == "2":
            packages.append("unbound")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y"] + packages, check=True)

    def _setup_pki(self):
        """Initializes the PKI and generates an initial Certificate Revocation List."""
        print("[2/7] Setting up Public Key Infrastructure (PKI)...")
        if os.path.exists(self.EASYRSA_DIR):
             shutil.rmtree(self.EASYRSA_DIR)
        shutil.copytree("/usr/share/easy-rsa/", self.EASYRSA_DIR)
        easyrsa_script_path = os.path.join(self.EASYRSA_DIR, "easyrsa")
        os.chmod(easyrsa_script_path, 0o755)

        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "init-pki"], check=True, capture_output=True)
        subprocess.run(["./easyrsa", "--batch", "build-ca", "nopass"], check=True, capture_output=True)
        subprocess.run(["./easyrsa", "--batch", "build-server-full", "server-cert", "nopass"], check=True, capture_output=True)
        subprocess.run(["./easyrsa", "gen-dh"], check=True, capture_output=True)
        
        # CRITICAL: Generate the initial CRL file required for the server to start.
        subprocess.run(["./easyrsa", "gen-crl"], check=True, capture_output=True)

        # Copy all necessary files to /etc/openvpn
        shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/issued/server-cert.crt", f"{self.OPENVPN_DIR}/server-cert.crt")
        shutil.copy(f"{self.PKI_DIR}/private/ca.key", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/private/server-cert.key", f"{self.OPENVPN_DIR}/server-cert.key")
        shutil.copy(f"{self.PKI_DIR}/dh.pem", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR) # Copy the newly created CRL

    def _generate_server_configs(self):
        print("[3/7] Generating server configurations...")
        os.makedirs(self.SERVER_CONFIG_DIR, exist_ok=True)
        
        for path in ["/var/log/openvpn", "/var/run/openvpn"]:
            os.makedirs(path, exist_ok=True)
            shutil.chown(path, user="nobody", group="nogroup")

        base_config = self._get_base_config()
        cert_config = base_config.format(port=self.settings["cert_port"], proto=self.settings["cert_proto"], extra_auth="")
        with open(f"{self.SERVER_CONFIG_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        login_config = base_config.format(port=self.settings["login_port"], proto=self.settings["login_proto"], extra_auth='plugin /usr/lib/openvpn/openvpn-plugin-auth-pam.so openvpn\nverify-client-cert none')
        with open(f"{self.SERVER_CONFIG_DIR}/server-login.conf", "w") as f:
            f.write(login_config)

    def _setup_firewall_rules(self):
        print("[4/7] Setting up firewall rules...")
        net_interface = self._get_primary_interface()
        check_command = f"iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        if subprocess.run(check_command, shell=True, capture_output=True).returncode != 0:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        subprocess.run(f"iptables-save > {self.FIREWALL_RULES_V4}", shell=True, check=True)

    def _enable_ip_forwarding(self):
        print("[5/7] Enabling IP forwarding...")
        with open("/etc/sysctl.conf", "r+") as f:
            content = f.read()
            if "net.ipv4.ip_forward=1" not in content:
                f.seek(0, 2)
                f.write("\nnet.ipv4.ip_forward=1\n")
        subprocess.run(["sysctl", "-p"], check=True, capture_output=True)

    def _setup_pam(self):
        print("[6/7] Configuring PAM for OpenVPN...")
        pam_config = "auth required pam_unix.so shadow nodelay\naccount required pam_unix.so\n"
        with open("/etc/pam.d/openvpn", "w") as f:
            f.write(pam_config)

    def _setup_unbound(self):
        # Implementation for Unbound setup
        pass

    def _start_openvpn_services(self, silent=False):
        """Enables and starts the two OpenVPN systemd services."""
        if not silent:
            print("[7/7] Starting OpenVPN services...")
        
        # On modern systems, a restart is often required if the service fails to start initially.
        # We try to restart instead of just starting.
        commands = [
            ["systemctl", "daemon-reload"],
            ["systemctl", "enable", "openvpn-server@server-cert"],
            ["systemctl", "enable", "openvpn-server@server-login"],
            ["systemctl", "restart", "openvpn-server@server-cert"],
            ["systemctl", "restart", "openvpn-server@server-login"]
        ]
        for cmd in commands:
             subprocess.run(cmd, check=True, capture_output=silent)

    def create_user_certificate(self, username: str):
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "build-client-full", username, "nopass"], check=True, capture_output=True)

    def revoke_user_certificate(self, username: str):
        cert_path = f"{self.PKI_DIR}/issued/{username}.crt"
        if not os.path.exists(cert_path):
            return
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "revoke", username], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["./easyrsa", "gen-crl"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        self._start_openvpn_services(silent=True)

    def generate_user_config(self, username: str) -> str:
        client_config_template = f"""
client
dev tun
proto {self.settings.get("cert_proto", "udp")}
remote {self.settings.get("public_ip")} {self.settings.get("cert_port", "1194")}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher {self.settings.get("cipher", "AES-256-GCM")}
verb 3
<ca>
{self._read_file(f"{self.OPENVPN_DIR}/ca.crt")}
</ca>
<cert>
{self._read_file(f"{self.PKI_DIR}/issued/{username}.crt")}
</cert>
<key>
{self._read_file(f"{self.PKI_DIR}/private/{username}.key")}
</key>
"""
        return client_config_template

    def uninstall_openvpn(self):
        print("▶️  Starting uninstallation...")
        subprocess.run(["systemctl", "stop", "openvpn-server@server-cert"], check=False, capture_output=True)
        subprocess.run(["systemctl", "stop", "openvpn-server@server-login"], check=False, capture_output=True)
        subprocess.run(["systemctl", "disable", "openvpn-server@server-cert"], check=False, capture_output=True)
        subprocess.run(["systemctl", "disable", "openvpn-server@server-login"], check=False, capture_output=True)
        if os.path.exists(self.SETTINGS_FILE):
             os.remove(self.SETTINGS_FILE)
        if os.path.exists(self.OPENVPN_DIR):
            shutil.rmtree(self.OPENVPN_DIR)
        if os.path.exists("/etc/pam.d/openvpn"):
            os.remove("/etc/pam.d/openvpn")
        if os.path.exists(self.FIREWALL_RULES_V4):
            os.remove(self.FIREWALL_RULES_V4)
        for path in ["/var/log/openvpn", "/var/run/openvpn"]:
            if os.path.exists(path):
                shutil.rmtree(path)
        packages = ["openvpn", "easy-rsa", "iptables-persistent"]
        if os.path.exists("/etc/unbound"):
            packages.append("unbound")
        subprocess.run(["apt-get", "remove", "--purge", "-y"] + packages, check=True, capture_output=True)
        subprocess.run(["apt-get", "autoremove", "-y"], check=True, capture_output=True)
        print("✅ Uninstallation complete.")

    def get_backup_assets(self) -> list[str]:
        # ... (implementation)
        pass

    def pre_restore(self):
        # ... (implementation)
        pass

    def post_restore(self):
        # ... (implementation)
        pass

    def _get_base_config(self) -> str:
        dns_lines = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.8.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"'
        }.get(self.settings.get("dns", "3"), "")

        return f"""
port {{port}}
proto {{proto}}
dev tun
topology subnet
ca {self.OPENVPN_DIR}/ca.crt
cert {self.OPENVPN_DIR}/server-cert.crt
key {self.OPENVPN_DIR}/server-cert.key
dh {self.OPENVPN_DIR}/dh.pem
crl-verify {self.OPENVPN_DIR}/crl.pem
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist /var/run/openvpn/ipp.txt
status /var/log/openvpn/openvpn-status.log
push "redirect-gateway def1 bypass-dhcp"
{dns_lines}
keepalive 10 120
cipher {self.settings.get("cipher", "AES-256-GCM")}
user nobody
group nogroup
persist-key
persist-tun
verb 3
{{extra_auth}}
"""

    def _get_primary_interface(self) -> str:
        try:
            result = subprocess.run("ip route get 8.8.8.8 | awk '{print $5; exit}'", shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            return "eth0"
            
    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return ""
