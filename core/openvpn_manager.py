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
    SERVER_CONFIG_DIR = f"{OPENVPN_DIR}/server" # Modern path for server configs
    EASYRSA_DIR = f"{OPENVPN_DIR}/easy-rsa"
    PKI_DIR = f"{EASYRSA_DIR}/pki"
    FIREWALL_RULES_V4 = "/etc/iptables/rules.v4"
    SETTINGS_FILE = f"{OPENVPN_DIR}/settings.json"
    
    def __init__(self):
        """
        Initializes the manager and immediately tries to load settings from the
        persistent settings file if it exists.
        """
        self.settings = {}
        self._load_settings()

    def _load_settings(self):
        """Loads installation settings from the JSON file."""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Warning: Could not load settings file: {e}")
                self.settings = {}

    def _save_settings(self):
        """Saves the current settings to the JSON file."""
        os.makedirs(self.OPENVPN_DIR, exist_ok=True)
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)

    # --- Installation Orchestration ---

    def install_openvpn(self, settings: dict):
        """
        Main entry point for a full system installation.
        Orchestrates all steps and saves settings upon successful completion.
        """
        print("▶️  Starting OpenVPN installation...")
        self.settings = settings
        
        self._install_prerequisites()
        self._setup_pki()
        self._generate_server_configs()
        self._setup_firewall_rules()
        self._enable_ip_forwarding()
        self._setup_pam()
        if self.settings.get("dns") == "2": # '2' is for Unbound
             self._setup_unbound()
        self._start_openvpn_services()
        
        # Save settings only after all steps have completed successfully
        self._save_settings()
        print("✅ OpenVPN installation phase completed and settings saved.")

    # --- Core Installation Steps ---

    def _install_prerequisites(self):
        """Installs all necessary system packages."""
        print("[1/7] Installing prerequisites...")
        packages = ["openvpn", "easy-rsa", "iptables-persistent", "openssl", "ca-certificates", "curl", "libpam-pwquality"]
        if self.settings.get("dns") == "2":
            packages.append("unbound")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y"] + packages, check=True)

    def _setup_pki(self):
        """Initializes the Public Key Infrastructure (PKI) using Easy-RSA."""
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

        # Copy essential files to the main OpenVPN directory, not the server-specific one.
        # The configs will reference these from the parent directory.
        shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/issued/server-cert.crt", f"{self.OPENVPN_DIR}/server-cert.crt")
        shutil.copy(f"{self.PKI_DIR}/private/ca.key", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/private/server-cert.key", f"{self.OPENVPN_DIR}/server-cert.key")
        shutil.copy(f"{self.PKI_DIR}/dh.pem", self.OPENVPN_DIR)

    def _generate_server_configs(self):
        """Generates the two OpenVPN server configuration files in the correct directory."""
        print("[3/7] Generating server configurations...")
        os.makedirs(self.SERVER_CONFIG_DIR, exist_ok=True) # Ensure the /etc/openvpn/server directory exists
        base_config = self._get_base_config()

        # Config 1: Certificate-based authentication
        cert_config = base_config.format(port=self.settings["cert_port"], proto=self.settings["cert_proto"], extra_auth="")
        with open(f"{self.SERVER_CONFIG_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        # Config 2: Username/Password-based authentication
        login_config = base_config.format(port=self.settings["login_port"], proto=self.settings["login_proto"], extra_auth='plugin /usr/lib/openvpn/openvpn-plugin-auth-pam.so openvpn\nverify-client-cert none')
        with open(f"{self.SERVER_CONFIG_DIR}/server-login.conf", "w") as f:
            f.write(login_config)

    def _setup_firewall_rules(self):
        """Sets up iptables rules for NAT and saves them."""
        print("[4/7] Setting up firewall rules...")
        net_interface = self._get_primary_interface()
        nat_rule = f"-t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        # Check if the rule already exists before adding
        check_command = f"iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        rule_exists = subprocess.run(check_command, shell=True, capture_output=True).returncode == 0
        if not rule_exists:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        subprocess.run(f"iptables-save > {self.FIREWALL_RULES_V4}", shell=True, check=True)

    def _enable_ip_forwarding(self):
        """Enables IP forwarding in the kernel."""
        print("[5/7] Enabling IP forwarding...")
        with open("/etc/sysctl.conf", "r+") as f:
            content = f.read()
            if "net.ipv4.ip_forward=1" not in content:
                f.seek(0, 2)
                f.write("\nnet.ipv4.ip_forward=1\n")
        subprocess.run(["sysctl", "-p"], check=True, capture_output=True)

    def _setup_pam(self):
        """Configures PAM for OpenVPN login authentication."""
        print("[6/7] Configuring PAM for OpenVPN...")
        pam_config = "auth required pam_unix.so shadow nodelay\naccount required pam_unix.so\n"
        with open("/etc/pam.d/openvpn", "w") as f:
            f.write(pam_config)

    def _setup_unbound(self):
        """Installs and configures Unbound as a local recursive DNS resolver."""
        # ... (code is correct, no changes needed)
        pass

    def _start_openvpn_services(self, silent=False):
        """Enables and starts the two OpenVPN systemd services."""
        if not silent:
            print("[7/7] Starting OpenVPN services...")
        capture = silent
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=capture)
        subprocess.run(["systemctl", "enable", "openvpn-server@server-cert"], check=True, capture_output=capture)
        subprocess.run(["systemctl", "enable", "openvpn-server@server-login"], check=True, capture_output=capture)
        subprocess.run(["systemctl", "restart", "openvpn-server@server-cert"], check=True, capture_output=capture)
        subprocess.run(["systemctl", "restart", "openvpn-server@server-login"], check=True, capture_output=capture)

    # --- User Management ---

    def create_user_certificate(self, username: str):
        # ... (code is correct, no changes needed)
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "build-client-full", username, "nopass"], check=True, capture_output=True)

    def revoke_user_certificate(self, username: str):
        # ... (code is correct, no changes needed)
        cert_path = f"{self.PKI_DIR}/issued/{username}.crt"
        if not os.path.exists(cert_path):
            return
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "revoke", username], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["./easyrsa", "gen-crl"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        crl_path = f"{self.PKI_DIR}/crl.pem"
        if os.path.exists(crl_path):
            shutil.copy(crl_path, self.OPENVPN_DIR)
        self._start_openvpn_services(silent=True)

    def generate_user_config(self, username: str) -> str:
        """Generates the .ovpn configuration file for a user using persisted settings."""
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

    # --- Uninstallation ---

    def uninstall_openvpn(self):
        # ... (code is correct, no changes needed)
        pass

    # --- IBackupable Interface ---

    def get_backup_assets(self) -> list[str]:
        # ... (code is correct, no changes needed)
        pass

    def pre_restore(self):
        # ... (code is correct, no changes needed)
        pass

    def post_restore(self):
        # ... (code is correct, no changes needed)
        pass

    # --- Helper Methods ---
    def _get_base_config(self) -> str:
        """
        Returns the shared base configuration string.
        Paths to certs are now relative to the /etc/openvpn/server/ directory.
        """
        dns_options = {
            "1": "", # System default
            "2": f'push "dhcp-option DNS 10.8.0.1"', # Unbound
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"', # Cloudflare
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"', # Google
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"' # AdGuard
        }
        dns_lines = dns_options.get(self.settings.get("dns", "3"), "")

        # IMPORTANT: Paths are now relative to /etc/openvpn/server/, so we need to go one level up.
        return f"""
port {{port}}
proto {{proto}}
dev tun
ca ../ca.crt
cert ../server-cert.crt
key ../server-cert.key
dh ../dh.pem
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ../ipp.txt
push "redirect-gateway def1 bypass-dhcp"
{dns_lines}
keepalive 10 120
cipher {self.settings.get("cipher", "AES-256-GCM")}
persist-key
persist-tun
status ../openvpn-status.log
verb 3
crl-verify ../crl.pem
{{extra_auth}}
"""

    def _get_primary_interface(self) -> str:
        # ... (code is correct, no changes needed)
        pass
            
    def _read_file(self, path: str) -> str:
        # ... (code is correct, no changes needed)
        pass
