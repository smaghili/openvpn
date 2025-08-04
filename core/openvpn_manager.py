import os
import subprocess
import shutil
import platform
from .backup_interface import IBackupable

class OpenVPNManager(IBackupable):
    """
    Manages the complete lifecycle of OpenVPN server instances, including installation,
    configuration, user management, and backup/restore operations.
    This class is the central point for all OpenVPN-related system interactions.
    """

    OPENVPN_DIR = "/etc/openvpn"
    EASYRSA_DIR = f"{OPENVPN_DIR}/easy-rsa"
    PKI_DIR = f"{EASYRSA_DIR}/pki"
    FIREWALL_RULES_V4 = "/etc/iptables/rules.v4"
    
    def __init__(self):
        # The settings dictionary will be populated during installation.
        self.settings = {}

    # --- Installation Orchestration ---

    def install_openvpn(self, settings: dict):
        """
        Main entry point for a full system installation.
        Orchestrates all the necessary steps in the correct order.
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
        
        print("✅ OpenVPN installation phase completed.")

    # --- Core Installation Steps ---

    def _install_prerequisites(self):
        """Installs all necessary system packages."""
        print("[1/7] Installing prerequisites...")
        packages = [
            "openvpn", "easy-rsa", "iptables-persistent", "openssl",
            "ca-certificates", "curl", "libpam-pwquality"
        ]
        # Conditionally add Unbound if the user selected it.
        if self.settings.get("dns") == "2":
            packages.append("unbound")

        # Update and install
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y"] + packages, check=True)

    def _setup_pki(self):
        """Initializes the Public Key Infrastructure (PKI) using Easy-RSA."""
        print("[2/7] Setting up Public Key Infrastructure (PKI)...")
        # Copy easy-rsa scripts to a working directory
        if os.path.exists(self.EASYRSA_DIR):
             shutil.rmtree(self.EASYRSA_DIR)
        shutil.copytree("/usr/share/easy-rsa/", self.EASYRSA_DIR)
        
        # Make the easyrsa script executable
        easyrsa_script_path = os.path.join(self.EASYRSA_DIR, "easyrsa")
        if os.path.exists(easyrsa_script_path):
            os.chmod(easyrsa_script_path, 0o755)

        # Create PKI and CA
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "init-pki"], check=True)
        # The 'nopass' option is critical for an unattended server setup
        subprocess.run(["./easyrsa", "--batch", "build-ca", "nopass"], check=True)

        # Generate server certificate and key
        subprocess.run(
            ["./easyrsa", "--batch", f"--req-cn=server-cert", "build-server-full", "server-cert", "nopass"],
            check=True
        )
        # Generate Diffie-Hellman parameters
        subprocess.run(["./easyrsa", "gen-dh"], check=True)

        # Copy essential files to the OpenVPN directory
        shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/issued/server-cert.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/private/ca.key", self.OPENVPN_DIR) # For easy user cert generation
        shutil.copy(f"{self.PKI_DIR}/private/server-cert.key", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/dh.pem", self.OPENVPN_DIR)

    def _generate_server_configs(self):
        """Generates the two OpenVPN server configuration files."""
        print("[3/7] Generating server configurations...")
        base_config = self._get_base_config()

        # Config 1: Certificate-based authentication
        cert_config = base_config.format(
            port=self.settings["cert_port"],
            proto=self.settings["cert_proto"],
            extra_auth=""  # No extra auth needed
        )
        with open(f"{self.OPENVPN_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        # Config 2: Username/Password-based authentication
        login_config = base_config.format(
            port=self.settings["login_port"],
            proto=self.settings["login_proto"],
            extra_auth='plugin /usr/lib/openvpn/openvpn-plugin-auth-pam.so openvpn\nverify-client-cert none'
        )
        with open(f"{self.OPENVPN_DIR}/server-login.conf", "w") as f:
            f.write(login_config)

    def _setup_firewall_rules(self):
        """Sets up iptables rules for NAT and saves them."""
        print("[4/7] Setting up firewall rules...")
        net_interface = self._get_primary_interface()
        
        # Define NAT rule
        nat_rule = f"-A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        
        # Apply the rule
        subprocess.run(f"iptables {nat_rule.replace('-A', '-I')}", shell=True, check=True) # Using -I to insert at top
        
        # Save the rules
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        subprocess.run(f"iptables-save > {self.FIREWALL_RULES_V4}", shell=True, check=True)

    def _enable_ip_forwarding(self):
        """Enables IP forwarding in the kernel."""
        print("[5/7] Enabling IP forwarding...")
        with open("/etc/sysctl.conf", "a") as f:
            f.write("\nnet.ipv4.ip_forward=1\n")
        # Apply changes immediately
        subprocess.run(["sysctl", "-p"], check=True)

    def _setup_pam(self):
        """Configures PAM for OpenVPN login authentication."""
        print("[6/7] Configuring PAM for OpenVPN...")
        pam_config = """
auth       required   pam_unix.so shadow nodelay
account    required   pam_unix.so
"""
        with open("/etc/pam.d/openvpn", "w") as f:
            f.write(pam_config)

    def _setup_unbound(self):
        """Installs and configures Unbound as a local recursive DNS resolver."""
        print("[Bonus Step] Configuring Unbound DNS server...")
        unbound_config = f"""
server:
    # The interface to listen on for DNS queries. 10.8.0.1 is the OpenVPN server itself.
    interface: {self.settings.get('public_ip')}
    interface: 127.0.0.1
    interface: 10.8.0.1
    
    # Allow queries from the local machine and the VPN client subnet.
    access-control: 127.0.0.1/32 allow
    access-control: 10.8.0.0/24 allow

    # Hide identity and version to prevent information leakage.
    hide-identity: yes
    hide-version: yes

    # Use modern DNS privacy and security features.
    harden-glue: yes
    harden-dnssec-stripped: yes
    
    # Cache settings
    cache-min-ttl: 3600
    cache-max-ttl: 86400

    # Use root hints to find root servers (less reliance on third parties).
    root-hints: "/usr/share/dns/root.hints"

# Forward all other queries to a trusted upstream DNS resolver (Cloudflare in this case).
forward-zone:
    name: "."
    forward-addr: 1.1.1.1
    forward-addr: 1.0.0.1
"""
        with open("/etc/unbound/unbound.conf.d/openvpn.conf", "w") as f:
            f.write(unbound_config)
            
        subprocess.run(["systemctl", "restart", "unbound"], check=True)
        subprocess.run(["systemctl", "enable", "unbound"], check=True)

    def _start_openvpn_services(self):
        """Enables and starts the two OpenVPN systemd services."""
        print("[7/7] Starting OpenVPN services...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "openvpn-server@server-cert"], check=True)
        subprocess.run(["systemctl", "enable", "openvpn-server@server-login"], check=True)
        subprocess.run(["systemctl", "restart", "openvpn-server@server-cert"], check=True)
        subprocess.run(["systemctl", "restart", "openvpn-server@server-login"], check=True)

    # --- User Management ---

    def create_user_certificate(self, username: str):
        """Generates a certificate for a new user."""
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(
            ["./easyrsa", "--batch", f"--req-cn={username}", "build-client-full", username, "nopass"],
            check=True
        )

    def revoke_user_certificate(self, username: str):
        """Revokes an existing user's certificate."""
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "revoke", username], check=True)
        # Generate a new Certificate Revocation List (CRL)
        subprocess.run(["./easyrsa", "gen-crl"], check=True)
        # Copy the new CRL to the OpenVPN directory
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        # Restart services to apply the new CRL
        self._start_openvpn_services()

    def generate_user_config(self, username: str) -> str:
        """Generates the .ovpn configuration file for a user."""
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
        """Completely removes OpenVPN and all related configurations."""
        print("▶️  Starting uninstallation...")
        
        # Stop and disable services
        subprocess.run(["systemctl", "stop", "openvpn-server@server-cert"], check=False)
        subprocess.run(["systemctl", "stop", "openvpn-server@server-login"], check=False)
        subprocess.run(["systemctl", "disable", "openvpn-server@server-cert"], check=False)
        subprocess.run(["systemctl", "disable", "openvpn-server@server-login"], check=False)
        if os.path.exists("/etc/unbound/unbound.conf.d/openvpn.conf"):
             subprocess.run(["systemctl", "stop", "unbound"], check=False)
             subprocess.run(["systemctl", "disable", "unbound"], check=False)

        # Remove configuration files and directories
        if os.path.exists(self.OPENVPN_DIR):
            shutil.rmtree(self.OPENVPN_DIR)
        if os.path.exists("/etc/pam.d/openvpn"):
            os.remove("/etc/pam.d/openvpn")
        if os.path.exists(self.FIREWALL_RULES_V4):
            os.remove(self.FIREWALL_RULES_V4)
        if os.path.exists("/etc/unbound/unbound.conf.d/openvpn.conf"):
            os.remove("/etc/unbound/unbound.conf.d/openvpn.conf")
            
        # Purge packages
        packages = ["openvpn", "easy-rsa", "iptables-persistent", "unbound"]
        subprocess.run(["apt-get", "remove", "--purge", "-y"] + packages, check=True)
        subprocess.run(["apt-get", "autoremove", "-y"], check=True)
        
        print("✅ Uninstallation complete.")

    # --- IBackupable Interface Implementation ---

    def get_backup_assets(self) -> list[str]:
        """
        Returns a list of critical file and directory paths for backup.
        This now includes the entire OpenVPN configuration directory and firewall rules.
        """
        assets = [self.OPENVPN_DIR]
        if os.path.exists(self.FIREWALL_RULES_V4):
            assets.append(self.FIREWALL_RULES_V4)
        return assets

    def pre_restore(self):
        """Stops all related services before restoring files."""
        print("... Stopping OpenVPN and related services for restore...")
        subprocess.run(["systemctl", "stop", "openvpn-server@server-cert"], check=False)
        subprocess.run(["systemctl", "stop", "openvpn-server@server-login"], check=False)
        if os.path.exists("/etc/unbound/unbound.conf.d/openvpn.conf"):
            subprocess.run(["systemctl", "stop", "unbound"], check=False)

    def post_restore(self):
        """
        Performs essential actions after files are restored.
        This includes setting correct permissions and restarting all services.
        """
        print("... Setting permissions and restarting services after restore...")
        
        # Set strict permissions for private keys for security
        if os.path.exists(f"{self.OPENVPN_DIR}/ca.key"):
            os.chmod(f"{self.OPENVPN_DIR}/ca.key", 0o600)
        if os.path.exists(f"{self.OPENVPN_DIR}/server-cert.key"):
            os.chmod(f"{self.OPENVPN_DIR}/server-cert.key", 0o600)

        # Make easy-rsa script executable again
        easyrsa_script_path = os.path.join(self.EASYRSA_DIR, "easyrsa")
        if os.path.exists(easyrsa_script_path):
            os.chmod(easyrsa_script_path, 0o755)

        # Apply firewall rules from the restored file
        if os.path.exists(self.FIREWALL_RULES_V4):
             subprocess.run(f"iptables-restore < {self.FIREWALL_RULES_V4}", shell=True, check=True)

        # Restart all services
        self._start_openvpn_services()
        if os.path.exists("/etc/unbound/unbound.conf.d/openvpn.conf"):
            subprocess.run(["systemctl", "restart", "unbound"], check=True)
            subprocess.run(["systemctl", "enable", "unbound"], check=True)


    # --- Helper Methods ---

    def _get_base_config(self) -> str:
        """Returns the shared base configuration string for both server types."""
        dns_options = {
            "1": "", # System default
            "2": f'push "dhcp-option DNS 10.8.0.1"', # Unbound
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"', # Cloudflare
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"', # Google
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"' # AdGuard
        }
        dns_lines = dns_options.get(self.settings.get("dns", "3"), "")

        return f"""
port {{port}}
proto {{proto}}
dev tun
ca ca.crt
cert server-cert.crt
key server-cert.key
dh dh.pem
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt
push "redirect-gateway def1 bypass-dhcp"
{dns_lines}
keepalive 10 120
cipher {self.settings.get("cipher", "AES-256-GCM")}
persist-key
persist-tun
status openvpn-status.log
verb 3
crl-verify crl.pem
{{extra_auth}}
"""

    def _get_primary_interface(self) -> str:
        """Detects the primary public network interface."""
        try:
            # Use 'ip route' to find the default route, which gives the primary interface
            result = subprocess.run(
                "ip route get 8.8.8.8 | awk '{print $5; exit}'",
                shell=True, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except Exception:
            # Fallback for systems where the above command might fail
            return "eth0"
            
    def _read_file(self, path: str) -> str:
        """Safely reads the content of a file."""
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return ""
