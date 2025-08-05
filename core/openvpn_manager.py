import os
import subprocess
import shutil
import json
from typing import Dict, Any, List, Optional
from .backup_interface import IBackupable
from config.shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
from config.config import VPNConfig, config
from core.types import Username, ConfigData, InstallSettings
from core.exceptions import (
    InstallationError, 
    CertificateGenerationError, 
    ServiceError, 
    ConfigurationError
)


class OpenVPNManager(IBackupable):
    """
    Manages the complete lifecycle of OpenVPN server instances, including installation,
    configuration, user management, and backup/restore operations.
    This class now persists its settings to a JSON file for stateful operation.
    """

    OPENVPN_DIR = config.OPENVPN_DIR
    SERVER_CONFIG_DIR = config.SERVER_CONFIG_DIR
    EASYRSA_DIR = config.EASYRSA_DIR
    PKI_DIR = config.PKI_DIR
    FIREWALL_RULES_V4 = config.FIREWALL_RULES_V4
    SETTINGS_FILE = config.SETTINGS_FILE
    
    def __init__(self) -> None:
        self.settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self) -> None:
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Warning: Could not load settings file: {e}")

    def _save_settings(self) -> None:
        os.makedirs(self.OPENVPN_DIR, exist_ok=True)
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def install_openvpn(self, settings: Dict[str, Any]) -> None:
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

    def _install_prerequisites(self) -> None:
        # This method remains unchanged
        print("[1/7] Installing prerequisites...")
        packages = ["openvpn", "easy-rsa", "iptables-persistent", "openssl", "ca-certificates", "curl", "libpam-pwquality"]
        if self.settings.get("dns") == "2":
            packages.append("unbound")
        
        print("   └── Updating package lists...")
        subprocess.run(["apt-get", "update"], check=True, capture_output=True)
        
        print("   └── Configuring firewall persistence...")
        subprocess.run(["debconf-set-selections"], input="iptables-persistent iptables-persistent/autosave_v4 boolean true\n", 
                      text=True, check=True, capture_output=True)
        subprocess.run(["debconf-set-selections"], input="iptables-persistent iptables-persistent/autosave_v6 boolean true\n", 
                      text=True, check=True, capture_output=True)
        
        print(f"   └── Installing {len(packages)} packages...")
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        subprocess.run(["apt-get", "install", "-y"] + packages, check=True, capture_output=True, env=env)
        print("   ✅ Prerequisites installed")


    def _setup_pki(self) -> None:
        # This method remains unchanged
        print("[2/7] Setting up Public Key Infrastructure (PKI)...")
        
        print("   └── Preparing Easy-RSA environment...")
        if os.path.exists(self.EASYRSA_DIR):
             shutil.rmtree(self.EASYRSA_DIR)
        shutil.copytree("/usr/share/easy-rsa/", self.EASYRSA_DIR)
        easyrsa_script_path = os.path.join(self.EASYRSA_DIR, "easyrsa")
        os.chmod(easyrsa_script_path, 0o755)

        os.chdir(self.EASYRSA_DIR)
        
        with open("vars", "w") as f:
            f.write('set_var EASYRSA_ALGO "ec"\n')
            f.write('set_var EASYRSA_CURVE "prime256v1"\n')

        import random
        import string
        server_cn = f"cn_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"
        server_name = f"server_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"
        
        print("   └── Initializing PKI structure...")
        subprocess.run(["./easyrsa", "init-pki"], check=True, capture_output=True)
        
        print("   └── Generating Certificate Authority...")
        subprocess.run(["./easyrsa", "--batch", f"--req-cn={server_cn}", "build-ca", "nopass"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CA_EXPIRE": "3650"})
        
        print("   └── Creating server certificate...")
        subprocess.run(["./easyrsa", "--batch", "build-server-full", server_name, "nopass"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CERT_EXPIRE": "3650"})
        
        print("   └── Generating certificate revocation list...")
        subprocess.run(["./easyrsa", "gen-crl"], check=True, capture_output=True, env={**os.environ, "EASYRSA_CRL_DAYS": "3650"})
        
        print("   └── Creating TLS encryption key...")
        subprocess.run(["openvpn", "--genkey", "--secret", "/etc/openvpn/tls-crypt.key"], check=True, capture_output=True)

        print("   └── Installing certificates...")
        shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/private/ca.key", self.OPENVPN_DIR)
        shutil.copy(f"{self.PKI_DIR}/issued/{server_name}.crt", f"{self.OPENVPN_DIR}/server-cert.crt")
        shutil.copy(f"{self.PKI_DIR}/private/{server_name}.key", f"{self.OPENVPN_DIR}/server-cert.key")
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        os.chmod(f"{self.OPENVPN_DIR}/crl.pem", 0o644)
        print("   ✅ PKI setup complete")

    def _generate_server_configs(self) -> None:
        # This method remains unchanged
        print("[3/7] Generating server configurations...")
        
        print("   └── Creating directory structure...")
        os.makedirs(self.SERVER_CONFIG_DIR, exist_ok=True)
        
        for path in ["/var/log/openvpn", "/var/run/openvpn", "/etc/openvpn/ccd"]:
            os.makedirs(path, exist_ok=True)
            shutil.chown(path, user="nobody", group="nogroup")

        monitoring_config = self._get_monitoring_config()

        print("   └── Generating certificate-based server config...")
        base_config = self._get_base_config()
        cert_config = base_config.format(port=self.settings["cert_port"], proto=self.settings["cert_proto"], extra_auth="") + monitoring_config
        with open(f"{self.SERVER_CONFIG_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        print("   └── Generating login-based server config...")
        login_config = self._get_login_config()
        with open(f"{self.SERVER_CONFIG_DIR}/server-login.conf", "w") as f:
            f.write(login_config + monitoring_config)
        print("   ✅ Server configurations created with monitoring hooks")

    def _setup_firewall_rules(self) -> None:
        # This method remains unchanged
        print("[4/7] Setting up firewall rules...")
        
        print(f"   └── Detecting network interface...")
        net_interface = self._get_primary_interface()
        print(f"   └── Using interface: {net_interface}")
        
        print("   └── Configuring NAT rules for certificate-based VPN...")
        check_command = f"iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        if subprocess.run(check_command, shell=True, capture_output=True, text=True).returncode != 0:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
        print("   └── Configuring NAT rules for login-based VPN...")
        check_command = f"iptables -t nat -C POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE"
        if subprocess.run(check_command, shell=True, capture_output=True, text=True).returncode != 0:
            subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE", shell=True, check=True)
        
        print("   └── Saving firewall rules...")
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        subprocess.run(f"iptables-save > {self.FIREWALL_RULES_V4}", shell=True, check=True)
        print("   ✅ Firewall rules configured")

    def _enable_ip_forwarding(self) -> None:
        # This method remains unchanged
        print("[5/7] Enabling IP forwarding...")
        print("   └── Configuring kernel parameters...")
        with open("/etc/sysctl.conf", "r+") as f:
            content = f.read()
            if "net.ipv4.ip_forward=1" not in content:
                f.seek(0, 2)
                f.write("\nnet.ipv4.ip_forward=1\n")
        print("   └── Applying kernel parameters...")
        subprocess.run(["sysctl", "-p"], check=True, capture_output=True)
        print("   ✅ IP forwarding enabled")

    def _setup_pam(self) -> None:
        # This method remains unchanged
        print("[6/7] Configuring PAM for OpenVPN...")
        print("   └── Setting up username/password authentication...")
        pam_config = "auth required pam_unix.so shadow nodelay\naccount required pam_unix.so\n"
        with open("/etc/pam.d/openvpn", "w") as f:
            f.write(pam_config)
        print("   ✅ PAM authentication configured")

    def _setup_unbound(self) -> None:
        # This method remains unchanged
        pass

    def _create_monitor_service_file(self) -> None:
        """Creates the systemd service file for the monitor with dynamic paths."""
        # Load environment configuration
        from config.env_loader import get_config_value
        
        # Get project root from environment variable or fallback to relative path
        project_root = get_config_value("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        management_port = get_config_value("OPENVPN_MANAGEMENT_PORT", "7505")
        
        service_content = f"""[Unit]
Description=OpenVPN Traffic Monitor Service
After=network.target openvpn-server@server-cert.service openvpn-server@server-login.service
Wants=openvpn-server@server-cert.service openvpn-server@server-login.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory={project_root}
Environment=MONITOR_INTERVAL=45
Environment=MAX_LOG_SIZE=10485760
Environment=PYTHONPATH={project_root}
Environment=PROJECT_ROOT={project_root}
Environment=OPENVPN_MANAGEMENT_PORT={management_port}
Environment=OPENVPN_LOG_FILE=/var/log/openvpn/traffic_monitor.log
ExecStart=/usr/bin/python3 {project_root}/scripts/monitor_service.py
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
LimitNOFILE=1024
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openvpn-monitor

[Install]
WantedBy=multi-user.target
"""
        
        service_file_path = "/etc/systemd/system/openvpn-monitor.service"
        with open(service_file_path, 'w') as f:
            f.write(service_content)

    def _start_openvpn_services(self, silent: bool = False) -> None:
        """Enables and starts OpenVPN and the monitoring service."""
        if not silent:
            print("[7/7] Starting all services...")
            print("   └── Creating monitor service file...")
        
        # Create the service file with dynamic paths
        self._create_monitor_service_file()
        
        if not silent:
            print("   └── Reloading systemd daemon...")
        
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)
        
        services_to_manage = [
            "openvpn-server@server-cert",
            "openvpn-server@server-login",
            "openvpn-monitor"
        ]
        
        for service in services_to_manage:
            if not silent:
                print(f"   └── Enabling {service}...")
            subprocess.run(["systemctl", "enable", service], check=True, capture_output=True)
            if not silent:
                print(f"   └── (Re)starting {service}...")
            subprocess.run(["systemctl", "restart", service], check=True, capture_output=True)
        
        if not silent:
            print("   ✅ All services started and enabled.")

    def create_user_certificate(self, username: Username) -> None:
        # This method remains unchanged
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "build-client-full", username, "nopass"], check=True, capture_output=True)

    def revoke_user_certificate(self, username: Username) -> None:
        # This method remains unchanged
        cert_path = f"{self.PKI_DIR}/issued/{username}.crt"
        if not os.path.exists(cert_path):
            return
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(["./easyrsa", "--batch", "revoke", username], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["./easyrsa", "gen-crl"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        self._start_openvpn_services(silent=True)

    def generate_user_config(self, username: Username) -> ConfigData:
        # This method remains unchanged
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

    def get_shared_config(self) -> ConfigData:
        # This method remains unchanged
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

    def uninstall_openvpn(self, silent: bool = False) -> None:
        """Stops and removes all services and files, including the monitor."""
        if not silent:
            print("▶️  Starting uninstallation...")

        services_to_stop = [
            "openvpn-monitor",
            "openvpn-server@server-cert",
            "openvpn-server@server-login"
        ]
        for service in services_to_stop:
            subprocess.run(["systemctl", "stop", service], check=False, capture_output=True)
            subprocess.run(["systemctl", "disable", service], check=False, capture_output=True)

        monitor_service_file = "/etc/systemd/system/openvpn-monitor.service"
        if os.path.exists(monitor_service_file):
            os.remove(monitor_service_file)
        subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)

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
        
        if not silent:
            print("✅ Uninstallation complete.")

    def get_backup_assets(self) -> List[str]:
        # This method remains unchanged
        return [self.SETTINGS_FILE, self.EASYRSA_DIR]

    def pre_restore(self) -> None:
        """Stops all related services before a restore operation."""
        services_to_stop = [
            "openvpn-monitor",
            "openvpn-server@server-cert",
            "openvpn-server@server-login"
        ]
        for service in services_to_stop:
            subprocess.run(["systemctl", "stop", service], check=False, capture_output=True)

    def post_restore(self) -> None:
        # This method remains unchanged
        self._load_settings() 
        self._start_openvpn_services(silent=True)

    def _get_base_config(self) -> str:
        # This method remains unchanged
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
        # This method remains unchanged
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

    def _get_monitoring_config(self) -> str:
        """Returns the config lines needed for traffic monitoring with dynamic paths."""
        # Load environment configuration
        from config.env_loader import get_config_value
        
        # Get project root from environment variable or fallback to relative path  
        project_root = get_config_value("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        on_connect_script = os.path.join(project_root, 'scripts', 'on_connect.py')
        on_disconnect_script = os.path.join(project_root, 'scripts', 'on_disconnect.py')
        
        # Get management port from environment or use default
        management_port = get_config_value("OPENVPN_MANAGEMENT_PORT", "7505")
        
        return f"""
# --- Traffic Monitoring Config ---
script-security 2
client-connect {on_connect_script}
client-disconnect {on_disconnect_script}
management 127.0.0.1 {management_port}
"""

    def _get_primary_interface(self) -> str:
        # This method remains unchanged
        try:
            result = subprocess.run("ip route get 8.8.8.8 | awk '{print $5; exit}'", shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            return "eth0"
            
    def _read_file(self, path: str) -> str:
        # This method remains unchanged
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return ""
    
    def _extract_certificate(self, path: str) -> str:
        # This method remains unchanged
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
