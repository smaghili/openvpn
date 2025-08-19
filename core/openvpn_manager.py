import os
import subprocess
import logging
from typing import Dict, Any, Optional, List
from .backup_interface import IBackupable
from .vpn_installation_manager import VPNInstallationManager
from .vpn_config_manager import VPNConfigManager
from .certificate_manager import CertificateManager
from .service_manager import ServiceManager
from .network_manager import NetworkManager
from .config_generator import ConfigGenerator
from config.config import VPNConfig
from core.types import Username, ConfigData
from core.exceptions import InstallationError, ServiceError, ConfigurationError
logger = logging.getLogger(__name__)
class OpenVPNManager(IBackupable):
    def __init__(self, config: VPNConfig):
        self.config = config
        self.installation_manager = VPNInstallationManager(config)
        self.config_manager = VPNConfigManager(config)
        self.cert_manager = CertificateManager(config)
        self.service_manager = ServiceManager()
        self.network_manager = NetworkManager(config)
        self.config_generator = ConfigGenerator(config)
        self.config_manager.load_settings()
    def install_openvpn(self, settings: Dict[str, Any]) -> None:
        self.config_manager.validate_config(settings)
        self.installation_manager.install_openvpn(settings)
        self.cert_manager.setup_pki()
        self.config_generator.generate_server_configs(settings)
        self.network_manager.setup_firewall_rules()
        self.network_manager.enable_ip_forwarding()
        self._setup_pam()
        if settings.get("dns") == "2":
            self._setup_unbound()
        self.service_manager.start_services(["openvpn@server-cert", "openvpn@server-login"])
        self.config_manager.save_settings(settings)
    def create_user_certificate(self, username: Username) -> None:
        self.cert_manager.create_user_certificate(username)
    def revoke_user_certificate(self, username: Username) -> None:
        self.cert_manager.revoke_user_certificate(username)
    def generate_user_config(self, username: Username) -> ConfigData:
        ca_cert = self._read_file("/etc/openvpn/ca.crt")
        user_cert = self._extract_certificate(f"{self.config.PKI_DIR}/issued/{username}.crt")
        user_key = self._read_file(f"{self.config.PKI_DIR}/private/{username}.key")
        tls_crypt_key = self._read_file("/etc/openvpn/tls-crypt.key")
        return self.config_manager.generate_user_config(username, ca_cert, user_cert, user_key, tls_crypt_key)
    def get_shared_config(self) -> ConfigData:
        ca_cert = self._read_file("/etc/openvpn/ca.crt")
        if not os.path.exists(f"{self.config.PKI_DIR}/issued/main.crt"):
            self.cert_manager.create_main_certificate()
        main_cert = self._extract_certificate(f"{self.config.PKI_DIR}/issued/main.crt")
        main_key = self._read_file(f"{self.config.PKI_DIR}/private/main.key")
        tls_crypt_key = self._read_file("/etc/openvpn/tls-crypt.key")
        if not main_cert or not main_key:
            raise RuntimeError("Main certificate not found. Please reinstall.")
        return self.config_manager.generate_shared_config(ca_cert, main_cert, main_key, tls_crypt_key)
    def uninstall_openvpn(self, silent: bool = False) -> None:
        self.installation_manager.uninstall_openvpn(silent)
    def start_services(self) -> None:
        self.service_manager.start_services(["openvpn@server-cert", "openvpn@server-login"])
    def stop_services(self) -> None:
        self.service_manager.stop_services(["openvpn@server-cert", "openvpn@server-login"])
    def restart_services(self) -> None:
        self.service_manager.restart_services(["openvpn@server-cert", "openvpn@server-login"])
    def get_service_status(self) -> Dict[str, str]:
        return self.service_manager.get_service_status(["openvpn@server-cert", "openvpn@server-login"])
    def _setup_pam(self) -> None:
        pam_config = """auth required pam_pwquality.so retry=3
auth required pam_unix.so
account required pam_unix.so
session required pam_unix.so"""
        os.makedirs(os.path.dirname(self.config.PAM_CONFIG_FILE), exist_ok=True)
        with open(self.config.PAM_CONFIG_FILE, "w") as f:
            f.write(pam_config)
    def _setup_unbound(self) -> None:
        unbound_config = """server:
    interface: 10.8.0.1
    port: 53
    do-ip4: yes
    do-ip6: no
    do-udp: yes
    do-tcp: yes
    access-control: 10.8.0.0/24 allow
    access-control: 10.9.0.0/24 allow
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    use-caps-for-id: yes
    cache-min-ttl: 3600
    cache-max-ttl: 86400
    prefetch: yes
    num-threads: 1
    msg-cache-slabs: 2
    rrset-cache-slabs: 2
    infra-cache-slabs: 2
    key-cache-slabs: 2
    rrset-cache-size: 256k
    msg-cache-size: 128k
    so-rcvbuf: 1m
    private-address: 192.168.0.0/16
    private-address: 169.254.0.0/16
    private-address: 172.16.0.0/12
    private-address: 10.0.0.0/8"""
        with open("/etc/unbound/unbound.conf", "w") as f:
            f.write(unbound_config)
        try:
            subprocess.run(["systemctl", "enable", "unbound"], check=True, capture_output=True)
            subprocess.run(["systemctl", "restart", "unbound"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to setup unbound: {e}")
    def _read_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except IOError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""
    def _extract_certificate(self, cert_path: str) -> str:
        try:
            with open(cert_path, "r") as f:
                content = f.read()
                start = content.find("-----BEGIN CERTIFICATE-----")
                end = content.find("-----END CERTIFICATE-----") + 25
                return content[start:end] if start != -1 and end != -1 else ""
        except IOError as e:
            logger.error(f"Failed to extract certificate from {cert_path}: {e}")
            return ""
    def create_backup(self) -> Dict[str, Any]:
        return {
            "type": "openvpn_manager",
            "data": {
                "settings": self.config_manager.settings,
                "certificates": self.cert_manager.get_certificate_info(),
                "services": self.get_service_status()
            }
        }
    def restore_backup(self, backup_data: Dict[str, Any]) -> None:
        if backup_data.get("type") != "openvpn_manager":
            raise ValueError("Invalid backup type")
        data = backup_data.get("data", {})
        if "settings" in data:
            self.config_manager.save_settings(data["settings"])
        if "certificates" in data:
            self.cert_manager.restore_certificates(data["certificates"])

    def get_backup_assets(self) -> List[str]:
        return [
            "/etc/openvpn",
            self.config.PKI_DIR,
            self.config.PAM_CONFIG_FILE,
            "/etc/systemd/system/openvpn@server-cert.service",
            "/etc/systemd/system/openvpn@server-login.service"
        ]

    def pre_restore(self) -> None:
        logger.info("Stopping OpenVPN services before restore...")
        self.stop_services()

    def post_restore(self) -> None:
        logger.info("Setting file permissions and restarting OpenVPN services...")
        
        try:
            subprocess.run(["chown", "-R", "root:root", "/etc/openvpn"], check=True)
            subprocess.run(["chmod", "-R", "600", "/etc/openvpn"], check=True)
            subprocess.run(["chmod", "755", "/etc/openvpn"], check=True)
            
            if os.path.exists(self.config.PKI_DIR):
                subprocess.run(["chown", "-R", "root:root", self.config.PKI_DIR], check=True)
                subprocess.run(["chmod", "-R", "600", self.config.PKI_DIR], check=True)
                subprocess.run(["chmod", "755", self.config.PKI_DIR], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to set file permissions: {e}")
        
        self.start_services()
