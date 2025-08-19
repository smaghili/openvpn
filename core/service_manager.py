import logging
from typing import List, Dict, Any
from core.async_process_manager import get_process_manager
logger = logging.getLogger(__name__)
class ServiceManager:
    def __init__(self):
        self.process_manager = get_process_manager()
    async def start_services(self, services: List[str]) -> Dict[str, bool]:
        logger.info(f"Starting services: {', '.join(services)}")
        results = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("start", service)
            results[service] = result.success
            if result.success:
                logger.info(f"Service {service} started successfully")
            else:
                logger.error(f"Failed to start service {service}: {result.stderr}")
        return results
    async def stop_services(self, services: List[str]) -> Dict[str, bool]:
        logger.info(f"Stopping services: {', '.join(services)}")
        results = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("stop", service)
            results[service] = result.success
            if result.success:
                logger.info(f"Service {service} stopped successfully")
            else:
                logger.warning(f"Failed to stop service {service}: {result.stderr}")
        return results
    async def restart_services(self, services: List[str]) -> Dict[str, bool]:
        logger.info(f"Restarting services: {', '.join(services)}")
        results = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("restart", service)
            results[service] = result.success
            if result.success:
                logger.info(f"Service {service} restarted successfully")
            else:
                logger.error(f"Failed to restart service {service}: {result.stderr}")
        return results
    async def enable_services(self, services: List[str]) -> Dict[str, bool]:
        logger.info(f"Enabling services: {', '.join(services)}")
        results = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("enable", service)
            results[service] = result.success
            if result.success:
                logger.info(f"Service {service} enabled successfully")
            else:
                logger.error(f"Failed to enable service {service}: {result.stderr}")
        return results
    async def disable_services(self, services: List[str]) -> Dict[str, bool]:
        logger.info(f"Disabling services: {', '.join(services)}")
        results = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("disable", service)
            results[service] = result.success
            if result.success:
                logger.info(f"Service {service} disabled successfully")
            else:
                logger.warning(f"Failed to disable service {service}: {result.stderr}")
        return results
    async def get_service_status(self, services: List[str]) -> Dict[str, str]:
        logger.info(f"Getting status for services: {', '.join(services)}")
        statuses = {}
        for service in services:
            result = await self.process_manager.run_systemctl_command("is-active", service)
            if result.success:
                status = "active" if result.return_code == 0 else "inactive"
            else:
                status = "unknown"
            statuses[service] = status
        return statuses
    async def reload_daemon(self) -> bool:
        logger.info("Reloading systemd daemon...")
        result = await self.process_manager.run_command(["systemctl", "daemon-reload"])
        if result.success:
            logger.info("Systemd daemon reloaded successfully")
        else:
            logger.error(f"Failed to reload systemd daemon: {result.stderr}")
        return result.success
    async def get_all_services_status(self) -> Dict[str, Any]:
        vpn_services = [
            "openvpn@server-cert",
            "openvpn@server-login",
            "openvpn-uds-monitor",
            "openvpn-api"
        ]
        statuses = await self.get_service_status(vpn_services)
        return {
            "services": statuses,
            "total_services": len(vpn_services),
            "active_services": sum(1 for status in statuses.values() if status == "active"),
            "inactive_services": sum(1 for status in statuses.values() if status == "inactive")
        }
