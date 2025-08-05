"""
Configuration management for VPN Manager.
Centralizes all configuration values and provides validation.
"""

import os
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from core.types import IPAddress, Port, InstallSettings
from core.exceptions import ConfigurationError, ValidationError
from config.env_loader import get_config_value
from config.paths import VPNPaths

@dataclass
class VPNConfig:
    """Central configuration class for VPN Manager."""
    
    # Directory paths - all loaded from environment variables
    OPENVPN_DIR: str = field(default_factory=VPNPaths.get_database_dir)
    SERVER_CONFIG_DIR: str = field(default_factory=VPNPaths.get_openvpn_server_dir)
    EASYRSA_DIR: str = field(default_factory=VPNPaths.get_easyrsa_dir)
    PKI_DIR: str = field(default_factory=VPNPaths.get_pki_dir)
    DATABASE_FILE: str = field(default_factory=VPNPaths.get_database_file)
    SETTINGS_FILE: str = field(init=False)
    
    # Network defaults
    DEFAULT_CERT_PORT: Port = 1194
    DEFAULT_LOGIN_PORT: Port = 1195
    DEFAULT_PROTOCOL: str = "udp"
    DEFAULT_CIPHER: str = "AES-256-GCM"
    DEFAULT_CERT_SIZE: str = "2048"
    DEFAULT_DNS: str = "3"
    
    # Certificate settings
    CERT_EXPIRE_DAYS: int = 3650
    CRL_EXPIRE_DAYS: int = 3650
    CA_EXPIRE_DAYS: int = 3650
    
    # Network subnets
    CERT_SUBNET: str = "10.8.0.0/24"
    LOGIN_SUBNET: str = "10.9.0.0/24"
    
    # System files
    FIREWALL_RULES_V4: str = "/etc/iptables/rules.v4"
    PAM_CONFIG_FILE: str = "/etc/pam.d/openvpn"
    
    # Validation patterns
    USERNAME_PATTERN: re.Pattern = field(default_factory=lambda: re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,31}$"))
    IP_PATTERN: re.Pattern = field(default_factory=lambda: re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"))
    
    def __post_init__(self):
        """Initialize computed fields after dataclass creation."""
        self.SETTINGS_FILE = os.path.join(self.OPENVPN_DIR, "settings.json")
    
    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username format."""
        config = VPNConfig()
        if not config.USERNAME_PATTERN.match(username):
            raise ValidationError(
                "username", 
                username, 
                "Must start with letter, contain only alphanumeric characters, underscore, or hyphen, and be 2-32 characters long"
            )
        return username
    
    @staticmethod
    def validate_ip_address(ip: str) -> IPAddress:
        """Validate IP address format."""
        config = VPNConfig()
        if not config.IP_PATTERN.match(ip):
            raise ValidationError("ip_address", ip, "Invalid IP address format")
        return ip
    
    @staticmethod
    def validate_port(port: int) -> Port:
        """Validate port number."""
        if not (1024 <= port <= 65535):
            raise ValidationError("port", str(port), "Port must be between 1024 and 65535")
        return port
    
    @staticmethod
    def validate_protocol(protocol: str) -> str:
        """Validate network protocol."""
        if protocol.lower() not in ["udp", "tcp"]:
            raise ValidationError("protocol", protocol, "Protocol must be 'udp' or 'tcp'")
        return protocol.lower()
    
    @staticmethod
    def validate_dns_choice(dns: str) -> str:
        """Validate DNS choice."""
        if dns not in ["1", "2", "3", "4", "5"]:
            raise ValidationError("dns", dns, "DNS choice must be between 1 and 5")
        return dns
    
    @staticmethod
    def validate_install_settings(settings: Dict[str, Any]) -> InstallSettings:
        """Validate and convert installation settings."""
        try:
            return InstallSettings(
                public_ip=VPNConfig.validate_ip_address(settings["public_ip"]),
                cert_port=VPNConfig.validate_port(int(settings["cert_port"])),
                cert_proto=VPNConfig.validate_protocol(settings["cert_proto"]),
                login_port=VPNConfig.validate_port(int(settings["login_port"])),
                login_proto=VPNConfig.validate_protocol(settings["login_proto"]),
                dns=VPNConfig.validate_dns_choice(settings["dns"]),
                cipher=settings.get("cipher", VPNConfig.DEFAULT_CIPHER),
                cert_size=settings.get("cert_size", VPNConfig.DEFAULT_CERT_SIZE)
            )
        except (KeyError, ValueError, ValidationError) as e:
            raise ConfigurationError(f"Invalid installation settings: {e}")
    
    def get_dns_config(self, dns_choice: str) -> str:
        """Get DNS configuration based on choice."""
        dns_configs = {
            "1": "",
            "2": f'push "dhcp-option DNS 10.8.0.1"',
            "3": 'push "dhcp-option DNS 1.1.1.1"\npush "dhcp-option DNS 1.0.0.1"',
            "4": 'push "dhcp-option DNS 8.8.8.8"\npush "dhcp-option DNS 8.8.4.4"',
            "5": 'push "dhcp-option DNS 94.140.14.14"\npush "dhcp-option DNS 94.140.15.15"'
        }
        return dns_configs.get(dns_choice, dns_configs["3"])

config = VPNConfig()