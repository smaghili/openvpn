#!/usr/bin/env python3
"""
Path management module for VPN Manager.
All paths are loaded from environment variables with sensible defaults.
"""
import os
from .env_loader import get_config_value

class VPNPaths:
    """Centralized path management using environment variables."""
    
    @staticmethod
    def get_project_root():
        """Get project root directory."""
        return get_config_value('PROJECT_ROOT', '/etc/owpanel')
    
    @staticmethod
    def get_database_file():
        """Get database file path."""
        return get_config_value('DATABASE_FILE', '/etc/owpanel/openvpn_data/vpn_manager.db')
    
    @staticmethod
    def get_database_dir():
        """Get database directory path."""
        return get_config_value('DATABASE_DIR', '/etc/owpanel/openvpn_data')
    
    @staticmethod
    def get_log_file():
        """Get main log file path."""
        return get_config_value('OPENVPN_LOG_FILE', '/var/log/openvpn/traffic_monitor.log')
    
    @staticmethod
    def get_log_dir():
        """Get log directory path."""
        return get_config_value('LOG_DIR', '/var/log/openvpn')
    
    @staticmethod
    def get_openvpn_config_dir():
        """Get OpenVPN configuration directory."""
        return get_config_value('OPENVPN_CONFIG_DIR', '/etc/openvpn')
    
    @staticmethod
    def get_openvpn_server_dir():
        """Get OpenVPN server configuration directory."""
        return get_config_value('OPENVPN_SERVER_DIR', '/etc/openvpn/server')
    
    @staticmethod
    def get_ccd_dir():
        """Get client configuration directory."""
        return get_config_value('OPENVPN_CCD_DIR', '/etc/openvpn/ccd')
    
    @staticmethod
    def get_ca_cert():
        """Get CA certificate path."""
        return get_config_value('CA_CERT', '/etc/openvpn/ca.crt')
    
    @staticmethod
    def get_server_cert():
        """Get server certificate path."""
        return get_config_value('SERVER_CERT', '/etc/openvpn/server-cert.crt')
    
    @staticmethod
    def get_server_key():
        """Get server key path."""
        return get_config_value('SERVER_KEY', '/etc/openvpn/server-cert.key')
    
    @staticmethod
    def get_crl_file():
        """Get CRL file path."""
        return get_config_value('CRL_FILE', '/etc/openvpn/crl.pem')
    
    @staticmethod
    def get_tls_crypt_key():
        """Get TLS crypt key path."""
        return get_config_value('TLS_CRYPT_KEY', '/etc/openvpn/tls-crypt.key')
    
    @staticmethod
    def get_easyrsa_dir():
        """Get EasyRSA directory path."""
        return get_config_value('EASYRSA_DIR', '/etc/openvpn/easy-rsa')
    
    @staticmethod
    def get_pki_dir():
        """Get PKI directory path."""
        return get_config_value('PKI_DIR', '/etc/openvpn/easy-rsa/pki')
    
    @staticmethod
    def get_scripts_dir():
        """Get scripts directory path."""
        return get_config_value('SCRIPTS_DIR', '/etc/owpanel/scripts')
    
    @staticmethod
    def get_on_connect_script():
        """Get on_connect script path."""
        return get_config_value('ON_CONNECT_SCRIPT', '/etc/owpanel/scripts/on_connect.py')
    
    @staticmethod
    def get_on_disconnect_script():
        """Get on_disconnect script path."""
        return get_config_value('ON_DISCONNECT_SCRIPT', '/etc/owpanel/scripts/on_disconnect.py')
    
    @staticmethod
    def get_status_file():
        """Get OpenVPN status file path."""
        return get_config_value('STATUS_FILE', '/var/log/openvpn/openvpn-status.log')
    
    @staticmethod
    def get_run_dir():
        """Get runtime directory path."""
        return get_config_value('VAR_RUN_OPENVPN', '/var/run/openvpn')

# Create a global instance for easy access
paths = VPNPaths()