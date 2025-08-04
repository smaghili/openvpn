import os
import subprocess
import shutil
import json
from .backup_interface import IBackupable
from config.shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE


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
        
        # Create a 'vars' file to configure Easy-RSA with modern settings
        with open("vars", "w") as f:
            f.write('set_var EASYRSA_ALGO "ec"\n')
            f.write('set_var EASYRSA_CURVE "prime256v1"\n')

        # Generate random server identifiers like install.sh
        import random
        import string
        server_cn = f"cn_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"
        server_name = f"server_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"
        
        subprocess.run(["./easyrsa", "init-pki"], check=True, capture_output=True)
        subprocess.run(["./easyrsa", "--batch", f"--req-cn={server_cn}", "build-ca", "nopass"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CA_EXPIRE": "3650"})
        subprocess.run(["./easyrsa", "--batch", "build-server-full", server_name, "nopass"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CERT_EXPIRE": "3650"})
        subprocess.run(["./easyrsa", "gen-crl"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CRL_DAYS": "3650"})
        subprocess.run(["openvpn", "--genkey", "--secret", "/etc/openvpn/tls-crypt.key"], check=True, capture_output=True)


        shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/private/ca.key", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/issued/{server_name}.crt", f"{self.OPENVPN_DIR}/server-cert.crt")
        shutil.copy(f"{self.PKI_DIR}/private/{server_name}.key", f"{self.OPENVPN_DIR}/server-cert.key")
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        os.chmod(f"{self.OPENVPN_DIR}/crl.pem", 0o644)

    def _generate_server_configs(self):
        print("[3/7] Generating server configurations...")
        os.makedirs(self.SERVER_CONFIG_DIR, exist_ok=True)
        
        for path in ["/var/log/openvpn", "/var/run/openvpn", "/etc/openvpn/ccd"]:
            os.makedirs(path, exist_ok=True)
            shutil.chown(path, user="nobody", group="nogroup")

        base_config = self._get_base_config()
        cert_config = base_config.format(port=self.settings["cert_port"], proto=self.settings["cert_proto"], extra_auth="")
        with open(f"{self.SERVER_CONFIG_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        login_config = self._get_login_config()
        with open(f"{self.SERVER_CONFIG_DIR}/server-login.conf", "w") as f:
            f.write(login_config)

    def _setup_firewall_rules(self):
        print("[4/7] Setting up firewall rules...")
        net_interface = self._get_primary_interface()
        
        # Certificate-based server (10.8.0.0/24)
        check_command = f"iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        if subprocess.run(check_command, shell=True, capture_output=True, text=True).returncode != 0:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
        # Login-based server (10.9.0.0/24)
        check_command = f"iptables -t nat -C POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE"
        if subprocess.run(check_command, shell=True, capture_output=True, text=True).returncode != 0:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
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
        ca_cert = self._read_file(f"{self.OPENVPN_DIR}/ca.crt")
        user_cert = self._extract_certificate(f"{self.PKI_DIR}/issued/{username}.crt")
        user_key = self._read_file(f"{self.PKI_DIR}/private/{username}.key")
        tls_crypt_key = self._read_file(f"{self.OPENVPN_DIR}/tls-crypt.key")

        user_specific_certs = USER_CERTS_TEMPLATE.format(user_cert=user_cert, user_key=user_key)
        
        return CLIENT_TEMPLATE.format(
            proto=self.settings.get("cert_proto", "udp"),
            server_ip=self.settings.get("public_ip"),
            port=self.settings.get("cert_port", "1194"),
            ca_cert=ca_cert,
            user_specific_certs=user_specific_certs,
            tls_crypt_key=tls_crypt_key
        )

    def get_shared_config(self) -> str:
        ca_cert = self._read_file(f"{self.OPENVPN_DIR}/ca.crt")
        
        if not os.path.exists(f"{self.PKI_DIR}/issued/main.crt"):
            os.chdir(self.EASYRSA_DIR)
            subprocess.run(["./easyrsa", "--batch", "build-client-full", "main", "nopass"], check=True, capture_output=True)
        
        main_cert = self._extract_certificate(f"{self.PKI_DIR}/issued/main.crt")
        main_key = self._read_file(f"{self.PKI_DIR}/private/main.key")
        tls_crypt_key = self._read_file(f"{self.OPENVPN_DIR}/tls-crypt.key")

        if not main_cert or not main_key:
            raise RuntimeError("Main certificate not found. Please reinstall.")

        server_protocol = self.settings.get("login_proto", "udp")
        server_ip = self.settings.get("public_ip")
        server_port = self.settings.get("login_port", "1195")
        cipher = self.settings.get("cipher", "AES-256-GCM")
        auth = "SHA256"

        config = f"""client
dev tun
proto {server_protocol}
remote {server_ip} {server_port}
resolv-retry infinite
nobind
persist-key
persist-tun
auth-user-pass
remote-cert-tls server
verb 3
cipher {cipher}
auth {auth}
tls-version-min 1.2
<ca>
{ca_cert}
</ca>
<cert>
{main_cert}
</cert>
<key>
{main_key}
</key>
<tls-crypt>
{tls_crypt_key}
</tls-crypt>"""
        
        return config

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
        """Returns the list of files essential for OpenVPN state."""
        return [self.SETTINGS_FILE, self.EASYRSA_DIR]

    def pre_restore(self):
        """Stops OpenVPN services before a restore operation."""
        print("Stopping OpenVPN services for restore...")
        subprocess.run(["systemctl", "stop", "openvpn-server@server-cert"], check=False, capture_output=True)
        subprocess.run(["systemctl", "stop", "openvpn-server@server-login"], check=False, capture_output=True)

    def post_restore(self):
        """Restarts OpenVPN services after a restore and reloads state."""
        print("Reloading settings and restarting OpenVPN services...")
        self._load_settings() 
        self._start_openvpn_services(silent=True)

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
dh none
ecdh-curve prime256v1
crl-verify {self.OPENVPN_DIR}/crl.pem
tls-crypt {self.OPENVPN_DIR}/tls-crypt.key
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

    def _get_login_config(self) -> str:
        dns_lines = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.9.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"'
        }.get(self.settings.get("dns", "3"), "")

        cipher_config = self.settings.get("cipher", "AES-256-GCM") + ":AES-128-GCM"
        cc_cipher_config = "TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256:TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256:TLS-ECDHE-RSA-WITH-AES-256-CBC-SHA384"

        return f"""port {self.settings["login_port"]}
proto {self.settings["login_proto"]}
dev tun1
topology subnet
ca {self.OPENVPN_DIR}/ca.crt
cert {self.OPENVPN_DIR}/server-cert.crt
key {self.OPENVPN_DIR}/server-cert.key
dh none
ecdh-curve prime256v1
server 10.9.0.0 255.255.255.0
ifconfig-pool-persist ipp-login.txt

# PAM authentication
plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn
username-as-common-name
verify-client-cert none

push "redirect-gateway def1 bypass-dhcp"
{dns_lines}
keepalive 10 120

# CRL verification
crl-verify {self.OPENVPN_DIR}/crl.pem
tls-crypt {self.OPENVPN_DIR}/tls-crypt.key
cipher {self.settings.get("cipher", "AES-256-GCM")}
ncp-ciphers {cipher_config}
tls-server
tls-version-min 1.2
tls-cipher {cc_cipher_config}
client-config-dir /etc/openvpn/ccd
user nobody
group nogroup
persist-key
persist-tun
status /var/log/openvpn/status-login.log
verb 3
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
    
    def _extract_certificate(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
                lines = content.split('\n')
                cert_lines = []
                in_cert = False
                for line in lines:
                    if '-----BEGIN CERTIFICATE-----' in line:
                        in_cert = True
                        cert_lines.append(line)
                    elif '-----END CERTIFICATE-----' in line:
                        cert_lines.append(line)
                        break
                    elif in_cert:
                        cert_lines.append(line)
                return '\n'.join(cert_lines)
        return ""