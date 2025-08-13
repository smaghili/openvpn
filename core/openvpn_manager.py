import os
import subprocess
import shutil
import json
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from .backup_interface import IBackupable
from config.shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
from config.config import VPNConfig, config, InstallSettings
from config.constants import OpenVPNConstants, ConfigurablePaths
from config.paths import VPNPaths
from core.types import Username, ConfigData
from core.exceptions import (
    InstallationError,
    CertificateGenerationError,
    ServiceError,
    ConfigurationError,
)

LOG_LEVEL = os.environ.get("OPENVPN_MANAGER_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get(
    "OPENVPN_MANAGER_LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


@contextmanager
def working_directory(path: str):
    """Temporarily change the working directory within a context."""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


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
                with open(self.SETTINGS_FILE, "r") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("⚠️  Warning: Could not load settings file: %s", e)

    def _save_settings(self) -> None:
        os.makedirs(self.OPENVPN_DIR, exist_ok=True)
        with open(self.SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

    def install_openvpn(self, settings: Dict[str, Any]) -> None:
        logger.info("▶️  Starting OpenVPN installation...")
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
        logger.info("[1/7] Installing prerequisites...")
        packages = [
            "openvpn",
            "easy-rsa",
            "iptables-persistent",
            "openssl",
            "ca-certificates",
            "curl",
            "libpam-pwquality",
        ]
        if self.settings.get("dns") == "2":
            packages.append("unbound")

        def _run(cmd: List[str], **kwargs) -> None:
            try:
                result = subprocess.run(
                    cmd, check=True, capture_output=True, text=True, **kwargs
                )
                if result.stdout:
                    logger.debug(result.stdout.strip())
                if result.stderr:
                    logger.debug(result.stderr.strip())
            except subprocess.CalledProcessError as exc:
                if exc.stdout:
                    logger.error(exc.stdout.strip())
                if exc.stderr:
                    logger.error(exc.stderr.strip())
                raise

        logger.info("   └── Updating package lists...")
        _run(["apt-get", "update"])

        logger.info("   └── Configuring firewall persistence...")
        _run(
            ["debconf-set-selections"],
            input="iptables-persistent iptables-persistent/autosave_v4 boolean true\n",
        )
        _run(
            ["debconf-set-selections"],
            input="iptables-persistent iptables-persistent/autosave_v6 boolean true\n",
        )

        logger.info("   └── Installing %d packages...", len(packages))
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        _run(["apt-get", "install", "-y"] + packages, env=env)
        logger.info("   ✅ Prerequisites installed")

    def _setup_pki(self) -> None:
        logger.info("[2/7] Setting up Public Key Infrastructure (PKI)...")

        logger.info("   └── Preparing Easy-RSA environment...")
        if os.path.exists(self.EASYRSA_DIR):
            shutil.rmtree(self.EASYRSA_DIR)
        shutil.copytree("/usr/share/easy-rsa/", self.EASYRSA_DIR)
        easyrsa_script_path = os.path.join(self.EASYRSA_DIR, "easyrsa")
        os.chmod(easyrsa_script_path, 0o755)

        with working_directory(self.EASYRSA_DIR):
            with open("vars", "w") as f:
                f.write('set_var EASYRSA_ALGO "ec"\n')
                f.write('set_var EASYRSA_CURVE "prime256v1"\n')

            import random
            import string

            server_cn = f"cn_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"
            server_name = f"server_{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

            logger.info("   └── Initializing PKI structure...")
            subprocess.run(["./easyrsa", "init-pki"], check=True, capture_output=True)

            logger.info("   └── Generating Certificate Authority...")
            subprocess.run(
                ["./easyrsa", "--batch", f"--req-cn={server_cn}", "build-ca", "nopass"],
                check=True,
                capture_output=True,
                env={**os.environ, "EASYRSA_CA_EXPIRE": "3650"},
            )

            logger.info("   └── Creating server certificate...")
            subprocess.run(
                ["./easyrsa", "--batch", "build-server-full", server_name, "nopass"],
                check=True,
                capture_output=True,
                env={**os.environ, "EASYRSA_CERT_EXPIRE": "3650"},
            )

            logger.info("   └── Generating certificate revocation list...")
            subprocess.run(
                ["./easyrsa", "gen-crl"],
                check=True,
                capture_output=True,
                env={**os.environ, "EASYRSA_CRL_DAYS": "3650"},
            )

            logger.info("   └── Creating TLS encryption key...")
            subprocess.run(
                ["openvpn", "--genkey", "--secret", "/etc/openvpn/tls-crypt.key"],
                check=True,
                capture_output=True,
            )
            if os.path.exists("/etc/openvpn/tls-crypt.key"):
                os.makedirs("/etc/openvpn/server", exist_ok=True)
                shutil.copy("/etc/openvpn/tls-crypt.key", "/etc/openvpn/server/")

            logger.info("   └── Installing certificates...")
            shutil.copy(f"{self.PKI_DIR}/ca.crt", "/etc/openvpn/")
            shutil.copy(f"{self.PKI_DIR}/private/ca.key", "/etc/openvpn/")
            shutil.copy(
                f"{self.PKI_DIR}/issued/{server_name}.crt",
                "/etc/openvpn/server-cert.crt",
            )
            shutil.copy(
                f"{self.PKI_DIR}/private/{server_name}.key",
                "/etc/openvpn/server-cert.key",
            )
            shutil.copy(f"{self.PKI_DIR}/crl.pem", "/etc/openvpn/")
            os.chmod("/etc/openvpn/crl.pem", 0o644)

            os.makedirs("/etc/openvpn/server", exist_ok=True)
            shutil.copy(f"{self.PKI_DIR}/ca.crt", "/etc/openvpn/server/")
            shutil.copy(
                f"{self.PKI_DIR}/issued/{server_name}.crt",
                "/etc/openvpn/server/server-cert.crt",
            )
            shutil.copy(
                f"{self.PKI_DIR}/private/{server_name}.key",
                "/etc/openvpn/server/server-cert.key",
            )
            shutil.copy(f"{self.PKI_DIR}/crl.pem", "/etc/openvpn/server/")
            os.chmod("/etc/openvpn/server/crl.pem", 0o644)

            shutil.copy(f"{self.PKI_DIR}/ca.crt", self.OPENVPN_DIR)
            shutil.copy(
                f"{self.PKI_DIR}/issued/{server_name}.crt",
                f"{self.OPENVPN_DIR}/server-cert.crt",
            )
            shutil.copy(
                f"{self.PKI_DIR}/private/{server_name}.key",
                f"{self.OPENVPN_DIR}/server-cert.key",
            )
            shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
            logger.info("   ✅ PKI setup complete")

    def _generate_server_configs(self) -> None:
        logger.info("[3/7] Generating server configurations...")

        logger.info("   └── Creating directory structure...")
        os.makedirs(self.SERVER_CONFIG_DIR, exist_ok=True)

        # Link scripts directory instead of copying files
        scripts_dir = VPNPaths.get_scripts_dir()
        openvpn_scripts_dir = "/etc/openvpn/scripts"

        if os.path.exists(scripts_dir):
            logger.info("   └── Setting up monitoring scripts...")
            if os.path.lexists(openvpn_scripts_dir):
                if os.path.islink(openvpn_scripts_dir):
                    os.remove(openvpn_scripts_dir)
                else:
                    shutil.rmtree(openvpn_scripts_dir)
            os.symlink(scripts_dir, openvpn_scripts_dir)

            # Ensure scripts are executable
            for script_name in ["on_connect.py", "on_disconnect.py"]:
                script_path = os.path.join(scripts_dir, script_name)
                if os.path.exists(script_path):
                    os.chmod(script_path, 0o755)
            os.chmod(scripts_dir, 0o755)

            # Link environment file for script access
            env_source = os.path.join(VPNPaths.get_project_root(), ".env")
            env_target = "/etc/openvpn/.env"
            if os.path.exists(env_source):
                try:
                    if os.path.islink(env_target) or os.path.exists(env_target):
                        os.remove(env_target)
                    os.symlink(env_source, env_target)
                except Exception:
                    shutil.copy(env_source, env_target)
                os.chmod(env_target, 0o600)

        # Ensure database file has correct permissions
        db_file = VPNPaths.get_database_file()
        db_dir = os.path.dirname(db_file)
        os.makedirs(db_dir, exist_ok=True)
        try:
            shutil.chown(db_dir, user="nobody", group="nogroup")
            os.chmod(db_dir, 0o770)
        except Exception as e:
            print(f"   └── Warning: could not set permissions on {db_dir}: {e}")

        if os.path.exists(db_file) and not os.access(db_file, os.W_OK):
            try:
                shutil.chown(db_file, user="nobody", group="nogroup")
                os.chmod(db_file, 0o660)
            except Exception as e:
                print(f"   └── Warning: could not set permissions on {db_file}: {e}")

        # Create required system directories
        system_dirs = [
            OpenVPNConstants.VAR_LOG_OPENVPN,
            OpenVPNConstants.VAR_RUN_OPENVPN,
        ]

        for path in system_dirs:
            os.makedirs(path, exist_ok=True)
            shutil.chown(path, user="nobody", group="nogroup")

        # CCD directory should be in the OpenVPN system directory
        os.makedirs(OpenVPNConstants.CCD_DIR, exist_ok=True)
        shutil.chown(OpenVPNConstants.CCD_DIR, user="nobody", group="nogroup")

        # Remove this line as we're using specific configs now

        logger.info("   └── Generating certificate-based server config...")
        base_config = self._get_base_config()
        cert_monitoring_config = self._get_monitoring_config(service_type="cert")
        cert_config = (
            base_config.format(
                port=self.settings["cert_port"],
                proto=self.settings["cert_proto"],
                extra_auth="",
            )
            + cert_monitoring_config
        )
        # Write to /etc/openvpn/server/server-cert.conf for systemd service
        os.makedirs("/etc/openvpn/server", exist_ok=True)
        with open("/etc/openvpn/server/server-cert.conf", "w") as f:
            f.write(cert_config)
        # Also write to legacy location for compatibility
        with open("/etc/openvpn/server-cert.conf", "w") as f:
            f.write(cert_config)
        # Also write to config directory for management
        with open(f"{self.SERVER_CONFIG_DIR}/server-cert.conf", "w") as f:
            f.write(cert_config)

        logger.info("   └── Generating login-based server config...")
        login_config = self._get_login_config()
        login_monitoring_config = self._get_monitoring_config(service_type="login")
        # Write to /etc/openvpn/server/server-login.conf for systemd service
        with open("/etc/openvpn/server/server-login.conf", "w") as f:
            f.write(login_config + login_monitoring_config)
        # Also write to legacy location for compatibility
        with open("/etc/openvpn/server-login.conf", "w") as f:
            f.write(login_config + login_monitoring_config)
        # Also write to config directory for management
        with open(f"{self.SERVER_CONFIG_DIR}/server-login.conf", "w") as f:
            f.write(login_config + login_monitoring_config)
        logger.info("   ✅ Server configurations created with monitoring hooks")

    def _setup_firewall_rules(self) -> None:
        # This method remains unchanged
        logger.info("[4/7] Setting up firewall rules...")

        logger.info("   └── Detecting network interface...")
        net_interface = self._get_primary_interface()
        logger.info("   └── Using interface: %s", net_interface)

        logger.info("   └── Configuring NAT rules for certificate-based VPN...")
        check_command = f"iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE"
        if (
            subprocess.run(
                check_command, shell=True, capture_output=True, text=True
            ).returncode
            != 0
        ):
            subprocess.run(
                f"iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o {net_interface} -j MASQUERADE",
                shell=True,
                check=True,
            )

        logger.info("   └── Configuring NAT rules for login-based VPN...")
        check_command = f"iptables -t nat -C POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE"
        if (
            subprocess.run(
                check_command, shell=True, capture_output=True, text=True
            ).returncode
            != 0
        ):
            subprocess.run(
                f"iptables -t nat -A POSTROUTING -s 10.9.0.0/24 -o {net_interface} -j MASQUERADE",
                shell=True,
                check=True,
            )
        logger.info("   └── Saving firewall rules...")
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        subprocess.run(
            f"iptables-save > {self.FIREWALL_RULES_V4}", shell=True, check=True
        )
        logger.info("   ✅ Firewall rules configured")

    def _enable_ip_forwarding(self) -> None:
        # This method remains unchanged
        logger.info("[5/7] Enabling IP forwarding...")
        logger.info("   └── Configuring kernel parameters...")
        with open("/etc/sysctl.conf", "r+") as f:
            content = f.read()
            if "net.ipv4.ip_forward=1" not in content:
                f.seek(0, 2)
                f.write("\nnet.ipv4.ip_forward=1\n")
        logger.info("   └── Applying kernel parameters...")
        subprocess.run(["sysctl", "-p"], check=True, capture_output=True)
        logger.info("   ✅ IP forwarding enabled")

    def _setup_pam(self) -> None:
        # This method remains unchanged
        logger.info("[6/7] Configuring PAM for OpenVPN...")
        logger.info("   └── Setting up username/password authentication...")
        pam_config = (
            "auth required pam_unix.so shadow nodelay\naccount required pam_unix.so\n"
        )
        with open("/etc/pam.d/openvpn", "w") as f:
            f.write(pam_config)
        logger.info("   ✅ PAM authentication configured")

    def _setup_unbound(self) -> None:
        # This method remains unchanged
        pass

    def _start_openvpn_services(self, silent: bool = False) -> None:
        """Enables and starts OpenVPN services."""
        if not silent:
            logger.info("[7/7] Starting all services...")
            logger.info("   └── Reloading systemd daemon...")

        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

        services_to_manage = [
            "openvpn-server@server-cert",
            "openvpn-server@server-login",
        ]

        for service in services_to_manage:
            if not silent:
                logger.info("   └── Enabling %s...", service)
            subprocess.run(
                ["systemctl", "enable", service], check=True, capture_output=True
            )
            if not silent:
                logger.info("   └── (Re)starting %s...", service)
            subprocess.run(
                ["systemctl", "restart", service], check=True, capture_output=True
            )

        if not silent:
            logger.info("   ✅ All services started and enabled.")

    def create_user_certificate(self, username: Username) -> None:
        # This method remains unchanged
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(
            ["./easyrsa", "--batch", "build-client-full", username, "nopass"],
            check=True,
            capture_output=True,
        )

    def revoke_user_certificate(self, username: Username) -> None:
        # This method remains unchanged
        cert_path = f"{self.PKI_DIR}/issued/{username}.crt"
        if not os.path.exists(cert_path):
            return
        os.chdir(self.EASYRSA_DIR)
        subprocess.run(
            ["./easyrsa", "--batch", "revoke", username],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["./easyrsa", "gen-crl"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.copy(f"{self.PKI_DIR}/crl.pem", self.OPENVPN_DIR)
        self._start_openvpn_services(silent=True)

    def generate_user_config(self, username: Username) -> ConfigData:
        # This method remains unchanged
        ca_cert = self._read_file("/etc/openvpn/ca.crt")
        user_cert = self._extract_certificate(f"{self.PKI_DIR}/issued/{username}.crt")
        user_key = self._read_file(f"{self.PKI_DIR}/private/{username}.key")
        tls_crypt_key = self._read_file("/etc/openvpn/tls-crypt.key")

        user_specific_certs = USER_CERTS_TEMPLATE.format(
            user_cert=user_cert, user_key=user_key
        )

        return CLIENT_TEMPLATE.format(
            proto=self.settings.get("cert_proto", "udp"),
            server_ip=self.settings.get("public_ip"),
            port=self.settings.get("cert_port", "1194"),
            ca_cert=ca_cert,
            user_specific_certs=user_specific_certs,
            tls_crypt_key=tls_crypt_key,
        )

    def get_shared_config(self) -> ConfigData:
        # This method remains unchanged
        ca_cert = self._read_file("/etc/openvpn/ca.crt")

        if not os.path.exists(f"{self.PKI_DIR}/issued/main.crt"):
            os.chdir(self.EASYRSA_DIR)
            subprocess.run(
                ["./easyrsa", "--batch", "build-client-full", "main", "nopass"],
                check=True,
                capture_output=True,
            )

        main_cert = self._extract_certificate(f"{self.PKI_DIR}/issued/main.crt")
        main_key = self._read_file(f"{self.PKI_DIR}/private/main.key")
        tls_crypt_key = self._read_file("/etc/openvpn/tls-crypt.key")

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
        """Completely removes all OpenVPN services, files, and processes."""
        if not silent:
            logger.info("▶️  Starting complete uninstallation...")

        if not silent:
            logger.info("   └── Force killing all OpenVPN processes...")
        subprocess.run(["killall", "-9", "openvpn"], check=False, capture_output=True)

        if not silent:
            logger.info("   └── Stopping and disabling services...")
        services_to_stop = [
            "openvpn-monitor",
            "openvpn-server@server-cert",
            "openvpn-server@server-login",
            "openvpn@server",
        ]
        for service in services_to_stop:
            subprocess.run(
                ["systemctl", "stop", service], check=False, capture_output=True
            )
            subprocess.run(
                ["systemctl", "disable", service], check=False, capture_output=True
            )

        if not silent:
            logger.info("   └── Removing service files...")
        monitor_service_file = "/etc/systemd/system/openvpn-monitor.service"
        if os.path.exists(monitor_service_file):
            os.remove(monitor_service_file)
        subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)

        if not silent:
            logger.info("   └── Cleaning configuration files...")
        config_paths = [
            self.SETTINGS_FILE,
            "/etc/openvpn/server-cert.conf",
            "/etc/openvpn/server-login.conf",
            "/etc/openvpn/server/server-cert.conf",
            "/etc/openvpn/server/server-login.conf",
            "/etc/pam.d/openvpn",
            self.FIREWALL_RULES_V4,
        ]
        for path in config_paths:
            if os.path.exists(path):
                os.remove(path)

        if not silent:
            logger.info("   └── Removing directories...")
        directories_to_remove = [
            self.OPENVPN_DIR,
            "/etc/openvpn/easy-rsa",
            "/etc/openvpn/server",
            "/etc/openvpn/ccd",
            "/etc/openvpn/scripts",
            "/var/log/openvpn",
            "/var/run/openvpn",
        ]
        for path in directories_to_remove:
            if not os.path.exists(path):
                continue
            if os.path.islink(path) or os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)

        if not silent:
            logger.info("   └── Removing certificate files...")
        cert_files = [
            "/etc/openvpn/ca.crt",
            "/etc/openvpn/ca.key",
            "/etc/openvpn/server-cert.crt",
            "/etc/openvpn/server-cert.key",
            "/etc/openvpn/crl.pem",
            "/etc/openvpn/tls-crypt.key",
        ]
        for path in cert_files:
            if os.path.exists(path):
                os.remove(path)

        if not silent:
            logger.info("   └── Final process cleanup...")

        if not silent:
            logger.info("   └── Removing packages...")
        packages = ["openvpn", "easy-rsa", "iptables-persistent"]
        if os.path.exists("/etc/unbound"):
            packages.append("unbound")
        subprocess.run(
            ["apt-get", "remove", "--purge", "-y"] + packages,
            check=True,
            capture_output=True,
        )
        subprocess.run(["apt-get", "autoremove", "-y"], check=True, capture_output=True)

        if not silent:
            logger.info("✅ Complete uninstallation finished. All ports freed.")

    def get_backup_assets(self) -> List[str]:
        # This method remains unchanged
        return [self.SETTINGS_FILE, self.EASYRSA_DIR]

    def pre_restore(self) -> None:
        """Stops all related services before a restore operation."""
        services_to_stop = [
            "openvpn-uds-monitor",
            "openvpn-server@server-cert",
            "openvpn-server@server-login",
        ]
        for service in services_to_stop:
            subprocess.run(
                ["systemctl", "stop", service], check=False, capture_output=True
            )

    def post_restore(self) -> None:
        # This method remains unchanged
        self._load_settings()
        self._start_openvpn_services(silent=True)

    def _get_base_config(self) -> str:
        # Use VPNPaths for all certificate and key paths
        from config.paths import VPNPaths

        dns_lines = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.8.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"',
        }.get(self.settings.get("dns", "3"), "")

        return f"""port {{port}}
proto {{proto}}
dev tun
topology subnet
ca ca.crt
cert server-cert.crt
key server-cert.key
dh none
ecdh-curve prime256v1
crl-verify crl.pem
tls-crypt tls-crypt.key
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist {OpenVPNConstants.VAR_RUN_OPENVPN}/ipp.txt
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
{{extra_auth}}"""

    def _get_login_config(self) -> str:
        # Generate login-based server configuration

        dns_lines = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.9.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"',
        }.get(self.settings.get("dns", "3"), "")

        cipher_config = self.settings.get("cipher", "AES-256-GCM") + ":AES-128-GCM"
        cc_cipher_config = "TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-CHACHA20-POLY1305-SHA256:TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256:TLS-ECDHE-RSA-WITH-AES-256-CBC-SHA384"

        return f"""port {self.settings["login_port"]}
proto {self.settings["login_proto"]}
dev tun1
topology subnet
ca ca.crt
cert server-cert.crt
key server-cert.key
dh none
ecdh-curve prime256v1
server 10.9.0.0 255.255.255.0
ifconfig-pool-persist {OpenVPNConstants.VAR_RUN_OPENVPN}/ipp-login.txt

# PAM authentication
plugin /usr/lib/x86_64-linux-gnu/openvpn/plugins/openvpn-plugin-auth-pam.so openvpn
username-as-common-name
verify-client-cert none

push "redirect-gateway def1 bypass-dhcp"
{dns_lines}
keepalive 10 120

# CRL verification
crl-verify crl.pem
tls-crypt tls-crypt.key
cipher {self.settings.get("cipher", "AES-256-GCM")}
ncp-ciphers {cipher_config}
tls-server
tls-version-min 1.2
tls-cipher {cc_cipher_config}
client-config-dir {OpenVPNConstants.CCD_DIR}
user nobody
group nogroup
persist-key
persist-tun
status /var/log/openvpn/status-login.log
verb 3"""

    def _get_monitoring_config(self, service_type: str = "cert") -> str:
        """Returns the config lines needed for traffic monitoring with UDS."""

        # Use different sockets for different services
        if service_type == "login":
            uds_socket = "/run/openvpn-server/ovpn-mgmt-login.sock"
        else:
            uds_socket = "/run/openvpn-server/ovpn-mgmt-cert.sock"

        on_connect_script = VPNPaths.get_on_connect_script()
        on_disconnect_script = VPNPaths.get_on_disconnect_script()

        return f"""
# --- Traffic Monitoring Config ---
script-security 2
client-connect {on_connect_script}
client-disconnect {on_disconnect_script}
management {uds_socket} unix
"""

    def _get_primary_interface(self) -> str:
        # This method remains unchanged
        try:
            result = subprocess.run(
                "ip route get 8.8.8.8 | awk '{print $5; exit}'",
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
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
                lines = content.split("\n")
                cert_lines = []
                in_cert = False
                for line in lines:
                    if "-----BEGIN CERTIFICATE-----" in line:
                        in_cert = True
                        cert_lines.append(line)
                    elif "-----END CERTIFICATE-----" in line:
                        cert_lines.append(line)
                        break
                    elif in_cert:
                        cert_lines.append(line)
                return "\n".join(cert_lines)
        return ""
