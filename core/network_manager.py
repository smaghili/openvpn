import os
import subprocess
from typing import Dict, Any
from config.config import VPNConfig
from core.logging_config import LoggerMixin

class NetworkManager(LoggerMixin):
    def __init__(self, config: VPNConfig):
        self.config = config
        self.FIREWALL_RULES_V4 = config.FIREWALL_RULES_V4
    def setup_firewall_rules(self) -> None:
        logger.info("[4/7] Configuring firewall rules...")
        logger.info("   └── Detecting network interface...")
        net_interface = self._get_primary_interface()
        logger.info("   └── Using interface: %s", net_interface)
        logger.info("   └── Configuring NAT rules for certificate-based VPN...")
        check_command = ["iptables", "-t", "nat", "-C", "POSTROUTING", "-s", "10.8.0.0/24", "-o", net_interface, "-j", "MASQUERADE"]
        if subprocess.run(check_command, capture_output=True, text=True).returncode != 0:
            subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", "10.8.0.0/24", "-o", net_interface, "-j", "MASQUERADE"], check=True)
        logger.info("   └── Configuring NAT rules for login-based VPN...")
        check_command = ["iptables", "-t", "nat", "-C", "POSTROUTING", "-s", "10.9.0.0/24", "-o", net_interface, "-j", "MASQUERADE"]
        if subprocess.run(check_command, capture_output=True, text=True).returncode != 0:
            subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", "10.9.0.0/24", "-o", net_interface, "-j", "MASQUERADE"], check=True)
        logger.info("   └── Saving firewall rules...")
        os.makedirs(os.path.dirname(self.FIREWALL_RULES_V4), exist_ok=True)
        with open(self.FIREWALL_RULES_V4, 'w') as f:
            subprocess.run(["iptables-save"], stdout=f, check=True)
        logger.info("   ✅ Firewall rules configured")
    def enable_ip_forwarding(self) -> None:
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
    def _get_primary_interface(self) -> str:
        result = subprocess.run(["ip", "route", "get", "8.8.8.8"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'dev' in line:
                parts = line.split()
                dev_index = parts.index('dev') + 1
                return parts[dev_index]
        return "eth0"
