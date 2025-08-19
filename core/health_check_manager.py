"""
Comprehensive health check system for monitoring all VPN Manager components.
Provides detailed system status and performance metrics.
"""

import time
import psutil
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.logging_config import LoggerMixin
from core.exceptions import HealthCheckError
from config.app_config import get_config
import os

class HealthCheckManager(LoggerMixin):
    """Comprehensive health check manager for system monitoring."""
    
    def __init__(self):
        self.config = get_config()
        self.last_check_time = 0
        self.check_interval = self.config.monitoring.interval
    
    def check_all_services(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all system components."""
        try:
            self.logger.info("Starting comprehensive health check")
            
            health_status = {
                "timestamp": time.time(),
                "overall_status": "healthy",
                "checks": {
                    "database": self._check_database(),
                    "system_resources": self._check_system_resources(),
                    "openvpn_service": self._check_openvpn_service(),
                    "cache_status": self._check_cache_status(),
                    "file_system": self._check_file_system(),
                    "network": self._check_network_status(),
                    "security": self._check_security_status()
                }
            }
            
            # Determine overall status
            failed_checks = [
                check for check in health_status["checks"].values()
                if check.get("status") == "unhealthy"
            ]
            
            if failed_checks:
                health_status["overall_status"] = "unhealthy"
                health_status["failed_checks"] = len(failed_checks)
            
            self.logger.info(
                "Health check completed",
                overall_status=health_status["overall_status"],
                failed_checks=len(failed_checks) if failed_checks else 0
            )
            
            return health_status
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            raise HealthCheckError(f"Health check failed: {e}")
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test database connection
            db_path = self.config.database.path
            if not Path(db_path).exists():
                return {
                    "status": "unhealthy",
                    "error": "Database file not found",
                    "path": db_path
                }
            
            # Test connection and basic query
            conn = sqlite3.connect(db_path, timeout=self.config.database.timeout)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Test performance
            cursor.execute("SELECT COUNT(*) FROM user_quotas")
            quota_count = cursor.fetchone()[0]
            
            conn.close()
            
            query_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "path": db_path,
                "user_count": user_count,
                "quota_count": quota_count,
                "query_time_ms": query_time * 1000,
                "file_size_mb": Path(db_path).stat().st_size / (1024 * 1024)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "path": self.config.database.path
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on thresholds
            cpu_status = "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "unhealthy"
            memory_status = "healthy" if memory.percent < 80 else "warning" if memory.percent < 95 else "unhealthy"
            disk_status = "healthy" if disk.percent < 80 else "warning" if disk.percent < 95 else "unhealthy"
            
            overall_status = "healthy"
            if any(status == "unhealthy" for status in [cpu_status, memory_status, disk_status]):
                overall_status = "unhealthy"
            elif any(status == "warning" for status in [cpu_status, memory_status, disk_status]):
                overall_status = "warning"
            
            return {
                "status": overall_status,
                "cpu": {
                    "percent": cpu_percent,
                    "status": cpu_status
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent,
                    "status": memory_status
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": disk.percent,
                    "status": disk_status
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_openvpn_service(self) -> Dict[str, Any]:
        """Check OpenVPN service status."""
        try:
            # Check if OpenVPN process is running
            openvpn_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'openvpn' in proc.info['name'].lower():
                        openvpn_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": proc.info['cmdline']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check OpenVPN status file
            status_file = "/var/log/openvpn/status.log"
            status_file_exists = Path(status_file).exists()
            
            if openvpn_processes:
                return {
                    "status": "healthy",
                    "processes": len(openvpn_processes),
                    "status_file_exists": status_file_exists,
                    "details": openvpn_processes
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "No OpenVPN processes found",
                    "status_file_exists": status_file_exists
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_cache_status(self) -> Dict[str, Any]:
        """Check cache system status."""
        try:
            from core.cache_manager import get_cache_manager
            
            cache_manager = get_cache_manager()
            
            # Test cache operations
            test_key = "health_check_test"
            test_value = {"timestamp": time.time()}
            
            # Test set
            cache_manager.set("test", test_key, test_value, ttl=60)
            
            # Test get
            retrieved_value = cache_manager.get("test", test_key)
            
            # Test delete
            cache_manager.delete("test", test_key)
            
            return {
                "status": "healthy",
                "enabled": self.config.cache.enabled,
                "operations": "set_get_delete_successful",
                "max_size": self.config.cache.max_size,
                "default_ttl": self.config.cache.default_ttl
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "enabled": self.config.cache.enabled
            }
    
    def _check_file_system(self) -> Dict[str, Any]:
        """Check critical file system paths."""
        try:
            critical_paths = [
                "/etc/owpanel",
                "/var/log/openvpn",
                "/etc/openvpn",
                self.config.database.path
            ]
            
            path_status = {}
            for path in critical_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    if path_obj.is_file():
                        path_status[path] = {
                            "exists": True,
                            "type": "file",
                            "size_bytes": path_obj.stat().st_size
                        }
                    else:
                        path_status[path] = {
                            "exists": True,
                            "type": "directory",
                            "writable": os.access(path, os.W_OK)
                        }
                else:
                    path_status[path] = {
                        "exists": False,
                        "type": "missing"
                    }
            
            missing_paths = [path for path, status in path_status.items() if not status["exists"]]
            
            return {
                "status": "healthy" if not missing_paths else "warning",
                "paths": path_status,
                "missing_paths": missing_paths
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_network_status(self) -> Dict[str, Any]:
        """Check network connectivity and interfaces."""
        try:
            # Check network interfaces
            interfaces = psutil.net_if_addrs()
            active_interfaces = []
            
            for interface, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == psutil.AF_INET:  # IPv4
                        active_interfaces.append({
                            "name": interface,
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
            
            # Check connectivity (basic ping test)
            import subprocess
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "8.8.8.8"],
                    capture_output=True,
                    timeout=5
                )
                internet_connectivity = result.returncode == 0
            except:
                internet_connectivity = False
            
            return {
                "status": "healthy",
                "interfaces": active_interfaces,
                "internet_connectivity": internet_connectivity,
                "interface_count": len(active_interfaces)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_security_status(self) -> Dict[str, Any]:
        """Check security configuration status."""
        try:
            security_checks = {
                "secret_key_configured": bool(self.config.security.secret_key),
                "api_key_configured": bool(self.config.security.api_key),
                "jwt_secret_configured": bool(self.config.security.jwt_secret),
                "database_permissions": self._check_database_permissions()
            }
            
            failed_checks = [check for check, status in security_checks.items() if not status]
            
            return {
                "status": "healthy" if not failed_checks else "unhealthy",
                "checks": security_checks,
                "failed_checks": failed_checks
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_database_permissions(self) -> bool:
        """Check database file permissions."""
        try:
            db_path = Path(self.config.database.path)
            if not db_path.exists():
                return False
            
            stat = db_path.stat()
            # Check if file is readable/writable by owner only
            return stat.st_mode & 0o777 == 0o600
            
        except Exception:
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics for monitoring."""
        try:
            health_status = self.check_all_services()
            
            metrics = {
                "timestamp": health_status["timestamp"],
                "overall_health": health_status["overall_status"],
                "system": {
                    "cpu_percent": health_status["checks"]["system_resources"]["cpu"]["percent"],
                    "memory_percent": health_status["checks"]["system_resources"]["memory"]["percent"],
                    "disk_percent": health_status["checks"]["system_resources"]["disk"]["percent"]
                },
                "database": {
                    "user_count": health_status["checks"]["database"].get("user_count", 0),
                    "query_time_ms": health_status["checks"]["database"].get("query_time_ms", 0),
                    "file_size_mb": health_status["checks"]["database"].get("file_size_mb", 0)
                },
                "openvpn": {
                    "process_count": health_status["checks"]["openvpn_service"].get("processes", 0),
                    "status": health_status["checks"]["openvpn_service"]["status"]
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error("Failed to get metrics", error=str(e))
            return {
                "timestamp": time.time(),
                "error": str(e)
            }

# Global health check manager instance
_health_check_manager: Optional[HealthCheckManager] = None

def get_health_check_manager() -> HealthCheckManager:
    """Get the global health check manager instance."""
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
    return _health_check_manager
