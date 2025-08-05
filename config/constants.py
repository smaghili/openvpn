"""
System constants for OpenVPN Manager.
These paths should NOT be changed as they are OpenVPN standards.
"""
import os

class OpenVPNConstants:
    """Immutable system paths and constants."""
    
    # OpenVPN standard paths - DO NOT CHANGE
    EASYRSA_DIR = "/etc/openvpn/easy-rsa"
    PKI_DIR = "/etc/openvpn/easy-rsa/pki"
    SERVER_CONFIG_DIR = "/etc/openvpn/server"
    CCD_DIR = "/etc/openvpn/ccd"
    
    # System log directories
    VAR_LOG_OPENVPN = "/var/log/openvpn"
    VAR_RUN_OPENVPN = "/var/run/openvpn"
    
    # Management ports
    MANAGEMENT_PORT_CERT = 7505
    MANAGEMENT_PORT_LOGIN = 7506
    
    # Monitor settings
    MONITOR_INTERVAL = 45
    MAX_LOG_SIZE = 10485760  # 10MB

class ConfigurablePaths:
    """Paths that can be configured via environment variables."""
    
    @staticmethod
    def get_project_root():
        return os.environ.get('PROJECT_ROOT', '/root/openvpn')
    
    @staticmethod
    def get_database_file():
        return os.environ.get('DATABASE_FILE', '/root/openvpn/openvpn_data/vpn_manager.db')
    
    @staticmethod
    def get_database_dir():
        return os.environ.get('DATABASE_DIR', '/root/openvpn/openvpn_data')
    
    @staticmethod
    def get_log_file():
        return os.environ.get('OPENVPN_LOG_FILE', '/var/log/openvpn/traffic_monitor.log')
    
    @staticmethod
    def get_scripts_dir():
        project_root = ConfigurablePaths.get_project_root()
        return os.path.join(project_root, 'scripts')
    
    @staticmethod
    def get_on_connect_script():
        return os.path.join(ConfigurablePaths.get_scripts_dir(), 'on_connect.py')
    
    @staticmethod
    def get_on_disconnect_script():
        return os.path.join(ConfigurablePaths.get_scripts_dir(), 'on_disconnect.py')