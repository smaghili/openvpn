import os
import shutil
from core.logging_config import LoggerMixin
from typing import Dict, Any, Optional
from contextlib import contextmanager
from core.exceptions import CertificateError
from core.async_process_manager import get_process_manager
from config.config import VPNConfig
@contextmanager
def working_directory(path: str):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

class CertificateManager(LoggerMixin):
    def __init__(self, config: VPNConfig):
        self.config = config
        self.process_manager = get_process_manager()
    async def setup_pki(self) -> None:
        logger.info("Setting up PKI infrastructure...")
        os.makedirs(self.config.PKI_DIR, exist_ok=True)
        with working_directory(self.config.EASYRSA_DIR):
            await self._initialize_pki()
            await self._generate_ca()
            await self._generate_dh_params()
            await self._generate_crl()
        await self._copy_certificates()
        logger.info("PKI setup completed successfully")
    async def _initialize_pki(self) -> None:
        result = await self.process_manager.run_easyrsa_command(["init-pki"], self.config.EASYRSA_DIR)
        if not result.success:
            raise CertificateError(f"Failed to initialize PKI: {result.stderr}")
    async def _generate_ca(self) -> None:
        result = await self.process_manager.run_easyrsa_command(["--batch", "build-ca", "nopass"], self.config.EASYRSA_DIR)
        if not result.success:
            raise CertificateError(f"Failed to generate CA: {result.stderr}")
    async def _generate_dh_params(self) -> None:
        result = await self.process_manager.run_easyrsa_command(["--batch", "gen-dh"], self.config.EASYRSA_DIR)
        if not result.success:
            raise CertificateError(f"Failed to generate DH parameters: {result.stderr}")
    async def _generate_crl(self) -> None:
        result = await self.process_manager.run_easyrsa_command(["--batch", "gen-crl"], self.config.EASYRSA_DIR)
        if not result.success:
            raise CertificateError(f"Failed to generate CRL: {result.stderr}")
    async def _copy_certificates(self) -> None:
        cert_files = [
            ("ca.crt", "/etc/openvpn/ca.crt"),
            ("ca.key", "/etc/openvpn/ca.key"),
            ("dh.pem", "/etc/openvpn/dh.pem"),
            ("crl.pem", "/etc/openvpn/crl.pem")
        ]
        for src, dst in cert_files:
            src_path = os.path.join(self.config.PKI_DIR, src)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst)
                os.chmod(dst, 0o600)
    async def create_server_certificate(self) -> None:
        logger.info("Creating server certificate...")
        with working_directory(self.config.EASYRSA_DIR):
            result = await self.process_manager.run_easyrsa_command(
                ["--batch", "build-server-full", "server", "nopass"], 
                self.config.EASYRSA_DIR
            )
            if not result.success:
                raise CertificateError(f"Failed to create server certificate: {result.stderr}")
        await self._copy_server_certificates()
    async def _copy_server_certificates(self) -> None:
        server_cert = os.path.join(self.config.PKI_DIR, "issued", "server.crt")
        server_key = os.path.join(self.config.PKI_DIR, "private", "server.key")
        if os.path.exists(server_cert) and os.path.exists(server_key):
            shutil.copy2(server_cert, "/etc/openvpn/server-cert.crt")
            shutil.copy2(server_key, "/etc/openvpn/server-cert.key")
            os.chmod("/etc/openvpn/server-cert.crt", 0o644)
            os.chmod("/etc/openvpn/server-cert.key", 0o600)
    async def create_user_certificate(self, username: str) -> None:
        logger.info(f"Creating certificate for user: {username}")
        with working_directory(self.config.EASYRSA_DIR):
            result = await self.process_manager.run_easyrsa_command(
                ["--batch", "build-client-full", username, "nopass"], 
                self.config.EASYRSA_DIR
            )
            if not result.success:
                raise CertificateError(f"Failed to create certificate for {username}: {result.stderr}")
        await self._update_crl()
    async def create_main_certificate(self) -> None:
        logger.info("Creating main certificate...")
        with working_directory(self.config.EASYRSA_DIR):
            result = await self.process_manager.run_easyrsa_command(
                ["--batch", "build-client-full", "main", "nopass"], 
                self.config.EASYRSA_DIR
            )
            if not result.success:
                raise CertificateError(f"Failed to create main certificate: {result.stderr}")
    async def revoke_user_certificate(self, username: str) -> None:
        logger.info(f"Revoking certificate for user: {username}")
        cert_path = os.path.join(self.config.PKI_DIR, "issued", f"{username}.crt")
        if not os.path.exists(cert_path):
            logger.warning(f"Certificate for {username} not found")
            return
        with working_directory(self.config.EASYRSA_DIR):
            result = await self.process_manager.run_easyrsa_command(
                ["--batch", "revoke", username], 
                self.config.EASYRSA_DIR
            )
            if not result.success:
                logger.error(f"Failed to revoke certificate for {username}: {result.stderr}")
                return
        await self._update_crl()
        await self._restart_services()
    async def _update_crl(self) -> None:
        with working_directory(self.config.EASYRSA_DIR):
            result = await self.process_manager.run_easyrsa_command(["gen-crl"], self.config.EASYRSA_DIR)
            if result.success:
                shutil.copy2(os.path.join(self.config.PKI_DIR, "crl.pem"), "/etc/openvpn/crl.pem")
                os.chmod("/etc/openvpn/crl.pem", 0o644)
    async def _restart_services(self) -> None:
        services = ["openvpn@server-cert", "openvpn@server-login"]
        for service in services:
            result = await self.process_manager.run_systemctl_command("restart", service)
            if not result.success:
                logger.warning(f"Failed to restart {service}: {result.stderr}")
    def get_certificate_info(self) -> Dict[str, Any]:
        cert_info = {
            "ca_exists": os.path.exists("/etc/openvpn/ca.crt"),
            "server_cert_exists": os.path.exists("/etc/openvpn/server-cert.crt"),
            "pki_directory": self.config.PKI_DIR,
            "certificates_count": 0
        }
        if os.path.exists(self.config.PKI_DIR):
            issued_dir = os.path.join(self.config.PKI_DIR, "issued")
            if os.path.exists(issued_dir):
                cert_info["certificates_count"] = len([
                    f for f in os.listdir(issued_dir) 
                    if f.endswith('.crt') and f != 'ca.crt'
                ])
        return cert_info
    async def restore_certificates(self, cert_data: Dict[str, Any]) -> None:
        logger.info("Restoring certificates from backup...")
        if not cert_data.get("ca_exists"):
            logger.warning("CA certificate not found in backup")
            return
        await self.setup_pki()
        if cert_data.get("server_cert_exists"):
            await self.create_server_certificate()
