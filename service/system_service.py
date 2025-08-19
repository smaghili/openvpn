import psutil
import os
import time
import subprocess
from typing import Dict, Any
from data.db import Database
from data.user_repository import UserRepository

class SystemService:
    _last_cpu_times = None
    _last_cpu_check = 0
    _cpu_cache_duration = 3  # Cache CPU for 3 seconds
    _service_cache = None
    _service_cache_time = 0
    _service_cache_duration = -1  # Cache services disabled (always fresh)
    _stats_cache = None
    _stats_cache_time = 0
    _stats_cache_duration = 4  # Cache full stats for 4 seconds
    _user_cache = None
    _user_cache_time = 0
    _user_cache_duration = 30  # Cache users for 30 seconds
    
    @classmethod
    def clear_service_cache(cls):
        """Clear service status cache to force refresh"""
        cls._service_cache = None
        cls._service_cache_time = 0
        logger.info("Service cache cleared")
    """System monitoring service for real-time statistics"""
    
    @classmethod
    def get_system_stats(cls) -> Dict[str, Any]:
        """Get real-time system statistics with heavy caching"""
        current_time = time.time()
        
        # Use full stats cache if available and fresh
        if (cls._stats_cache and 
            current_time - cls._stats_cache_time < cls._stats_cache_duration):
            return cls._stats_cache
            
        try:
            # Optimized CPU Usage (minimal calls)
            if current_time - cls._last_cpu_check > cls._cpu_cache_duration:
                cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking
                cls._last_cpu_check = current_time
            else:
                cpu_percent = psutil.cpu_percent(interval=None)  # Use cached
            
            cpu_count = psutil.cpu_count()
            
            # Memory Usage (lightweight)
            memory = psutil.virtual_memory()
            ram_percent = round(memory.percent, 1)
            ram_used_mb = round(memory.used / (1024 * 1024))
            ram_total_mb = round(memory.total / (1024 * 1024))
            
            # Swap Usage (lightweight)
            swap = psutil.swap_memory()
            swap_percent = round(swap.percent, 1)
            swap_used_mb = round(swap.used / (1024 * 1024))
            swap_total_mb = round(swap.total / (1024 * 1024))
            
            # Disk Usage (lightweight - cache this too)
            disk = psutil.disk_usage('/')
            disk_percent = round((disk.used / disk.total) * 100, 1)
            disk_used_gb = round(disk.used / (1024 * 1024 * 1024), 1)
            disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 1)
            
            return {
                'success': True,
                'data': {
                    'cpu': {
                        'percent': round(cpu_percent, 1),
                        'cores': cpu_count,
                        'detail': f'Core {cpu_count}'
                    },
                    'ram': {
                        'percent': ram_percent,
                        'used_mb': ram_used_mb,
                        'total_mb': ram_total_mb,
                        'detail': f'{ram_used_mb}/{ram_total_mb}MB'
                    },
                    'swap': {
                        'percent': swap_percent,
                        'used_mb': swap_used_mb,
                        'total_mb': swap_total_mb,
                        'detail': f'{swap_used_mb}/{swap_total_mb}MB' if swap_total_mb > 0 else 'No Swap'
                    },
                    'storage': {
                        'percent': round(disk_percent, 1),
                        'used_gb': disk_used_gb,
                        'total_gb': disk_total_gb,
                        'detail': f'{disk_used_gb}/{disk_total_gb}GB'
                    },
                    'users': cls._get_user_stats(),
                    'summary': {
                        'total_users': cls._get_total_users(),
                        'total_usage': f'{disk_used_gb}GB'
                    }
                }
            }
            
            # Cache the result
            cls._stats_cache = result
            cls._stats_cache_time = current_time
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get system stats: {str(e)}',
                'data': None
            }
    
    @classmethod
    def get_service_status(cls) -> Dict[str, Any]:
        """Get real-time service status with caching"""
        try:
            current_time = time.time()
            
            # Use cache if available and fresh (skip cache if duration is negative)
            if (cls._service_cache and cls._service_cache_duration > 0 and
                current_time - cls._service_cache_time < cls._service_cache_duration):
                return cls._service_cache
            
            # Check actual service status (lightweight checks)
            services = {
                'openvpn-uds-monitor': cls._check_uds_status(),
                'wireguard': cls._check_wireguard_status(),
                'openvpn@server-login': cls._check_openvpn_login_status(),
                'openvpn@server-cert': cls._check_openvpn_cert_status()
            }
            
            result = {
                'success': True,
                'data': services
            }
            
            # Cache the result
            cls._service_cache = result
            cls._service_cache_time = current_time
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get service status: {str(e)}',
                'data': None
            }
    
    @staticmethod
    def _check_uds_status() -> Dict[str, str]:
        """Check UDS monitoring service status"""
        try:
            result = os.popen('/usr/bin/systemctl is-active openvpn-uds-monitor 2>/dev/null').read().strip() 
            if result == 'active':
                return {'status': 'active', 'uptime': 'Active'}
            elif result == 'inactive':
                return {'status': 'inactive', 'uptime': 'Stopped'}
            elif result == 'failed':
                return {'status': 'failed', 'uptime': 'Failed'}
            else:
                return {'status': 'unknown', 'uptime': f'Unknown: {result}'}
        except Exception as e:
            return {'status': 'error', 'uptime': f'Error: {str(e)}'}
    

    @staticmethod
    def _check_wireguard_status() -> Dict[str, str]:
        """Check WireGuard service status"""
        try:
            # Check WireGuard interface
            result = os.popen('wg show 2>/dev/null').read().strip()
            if result:
                return {'status': 'active', 'uptime': 'Active'}
            else:
                return {'status': 'inactive', 'uptime': 'Stopped'}
        except:
            return {'status': 'inactive', 'uptime': 'Stopped'}

    @staticmethod
    def _check_openvpn_login_status() -> Dict[str, Any]:
        """Check OpenVPN login service status with resource usage"""
        try:
            # Check if OpenVPN login service is running with full path
            result = os.popen('/usr/bin/systemctl is-active openvpn@server-login 2>/dev/null').read().strip()
            
            if result == 'active':
                return {'status': 'active', 'uptime': 'Active', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            elif result == 'inactive':
                return {'status': 'inactive', 'uptime': 'Stopped', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            elif result == 'failed':
                return {'status': 'failed', 'uptime': 'Failed', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            else:
                return {'status': 'unknown', 'uptime': f'Unknown: {result}', 'cpu_usage': 0.0, 'memory_usage': 0.0}
        except Exception as e:
            return {'status': 'error', 'uptime': f'Error: {str(e)}', 'cpu_usage': 0.0, 'memory_usage': 0.0}

    @staticmethod
    def _check_openvpn_cert_status() -> Dict[str, Any]:
        """Check OpenVPN cert service status with resource usage"""
        try:
            # Check if OpenVPN cert service is running with full path
            result = os.popen('/usr/bin/systemctl is-active openvpn@server-cert 2>/dev/null').read().strip()
            
            if result == 'active':
                return {'status': 'active', 'uptime': 'Active', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            elif result == 'inactive':
                return {'status': 'inactive', 'uptime': 'Stopped', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            elif result == 'failed':
                return {'status': 'failed', 'uptime': 'Failed', 'cpu_usage': 0.0, 'memory_usage': 0.0}
            else:
                return {'status': 'unknown', 'uptime': f'Unknown: {result}', 'cpu_usage': 0.0, 'memory_usage': 0.0}
        except Exception as e:
            return {'status': 'error', 'uptime': f'Error: {str(e)}', 'cpu_usage': 0.0, 'memory_usage': 0.0}
    
    @staticmethod
    def control_service(service_name: str, action: str) -> Dict[str, Any]:
        SYSTEMCTL_PATH = '/usr/bin/systemctl'
        TIMEOUT_SECONDS = 10
        SUCCESS_STATES = {
            'start': {'active'},
            'stop': {'inactive', 'failed', 'dead'},
            'restart': {'active'}
        }
        PAM_SERVICES = {'openvpn@server-login'}
        
        if action not in SUCCESS_STATES:
            return {
                'success': False, 
                'message': f'Invalid action "{action}". Valid actions: {list(SUCCESS_STATES.keys())}',
                'status': None
            }
        
        try:
            if action == 'stop' and service_name in PAM_SERVICES:
                result = subprocess.run([SYSTEMCTL_PATH, 'stop', service_name], 
                                      capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
                cmd_result = result.stderr if result.stderr else result.stdout
            elif action == 'restart' and service_name in PAM_SERVICES:
                stop_result = subprocess.run([SYSTEMCTL_PATH, 'stop', service_name], 
                                           capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
                time.sleep(1)
                result = subprocess.run([SYSTEMCTL_PATH, 'start', service_name], 
                                      capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
                cmd_result = result.stderr if result.stderr else result.stdout
            else:
                result = subprocess.run([SYSTEMCTL_PATH, action, service_name], 
                                      capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
                cmd_result = result.stderr if result.stderr else result.stdout
            
            status_result = subprocess.run([SYSTEMCTL_PATH, 'is-active', service_name], 
                                         capture_output=True, text=True)
            status = status_result.stdout.strip()
            
            expected_states = SUCCESS_STATES[action]
            is_success = status in expected_states
            
            return {
                'success': is_success,
                'message': f'Service {service_name} {action} {"successful" if is_success else "failed"} (status: {status})',
                'output': cmd_result.strip(),
                'status': status
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': f'Service {service_name} {action} timed out after {TIMEOUT_SECONDS}s',
                'status': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Service {service_name} {action} failed: {str(e)}',
                'status': None
            }

    @staticmethod
    def get_service_logs(service_name: str, lines: int = 100, follow: bool = False) -> Dict[str, Any]:
        """Get service logs"""
        try:
            if follow:
                cmd = f'journalctl -u {service_name} -f --no-pager -n {lines}'
            else:
                cmd = f'journalctl -u {service_name} --no-pager -n {lines}'
            
            logs = os.popen(cmd).read()
            
            return {
                'success': True,
                'logs': logs,
                'service': service_name
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get logs for {service_name}: {str(e)}'
            }

    @staticmethod
    def get_log_file_path(service_name: str) -> str:
        """Get log file path for service"""
        log_map = {
            'openvpn': '/var/log/openvpn/openvpn.log',
            'openvpn@server-cert': '/var/log/openvpn/openvpn.log',
            'openvpn@server-login': '/var/log/openvpn/openvpn.log',
            'openvpn-uds-monitor': '/var/log/openvpn/traffic_monitor.log',
            'wireguard': '/var/log/syslog',
            'wg-quick@wg0': '/var/log/syslog',
            'system': '/var/log/syslog'
        }
        return log_map.get(service_name, f'/var/log/{service_name}.log')

    @staticmethod
    def get_system_uptime() -> Dict[str, Any]:
        """Get system uptime information"""
        try:
            uptime_output = os.popen('/usr/bin/uptime -p').read().strip()
            last_boot = os.popen('/usr/bin/who -b | /usr/bin/awk \'{print $3, $4}\'').read().strip()
            
            uptime_seconds = float(os.popen('/usr/bin/cat /proc/uptime | /usr/bin/cut -d\' \' -f1').read().strip())
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            uptime_formatted = f"{days}d {hours}h {minutes}m"
            
            return {
                'success': True,
                'data': {
                    'uptime_formatted': uptime_formatted,
                    'uptime_raw': uptime_output,
                    'last_boot': last_boot,
                    'uptime_seconds': uptime_seconds,
                    'uptime_parts': {
                        'days': days,
                        'hours': hours,
                        'minutes': minutes
                    }
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get system uptime: {str(e)}'
            }

    @staticmethod
    def get_timestamp() -> str:
        """Get current timestamp for file naming"""
        import datetime
        return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    @classmethod
    def _get_total_users(cls) -> int:
        """Get total number of users from database with caching"""
        try:
            current_time = time.time()
            
            # Use cache if available and fresh
            if (cls._user_cache and 
                current_time - cls._user_cache_time < cls._user_cache_duration):
                return cls._user_cache.get('total', 0)
            
            # Fetch fresh data
            db = Database()
            user_repo = UserRepository(db)
            users = user_repo.get_all_users()
            
            # Cache the users data
            if users:
                active_users = sum(1 for user in users if user.get('status') == 'active')
                cls._user_cache = {
                    'total': len(users),
                    'active': active_users,
                    'inactive': len(users) - active_users,
                    'users_data': users
                }
            else:
                cls._user_cache = {
                    'total': 0,
                    'active': 0,
                    'inactive': 0,
                    'users_data': []
                }
            
            cls._user_cache_time = current_time
            return cls._user_cache['total']
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    @classmethod
    def _get_user_stats(cls) -> Dict[str, Any]:
        """Get user statistics with caching"""
        try:
            current_time = time.time()
            
            # Use cache if available and fresh
            if (cls._user_cache and 
                current_time - cls._user_cache_time < cls._user_cache_duration):
                return {
                    'total': cls._user_cache.get('total', 0),
                    'active': cls._user_cache.get('active', 0),
                    'inactive': cls._user_cache.get('inactive', 0)
                }
            
            # If cache miss, trigger user count which will populate cache
            cls._get_total_users()
            
            return {
                'total': cls._user_cache.get('total', 0),
                'active': cls._user_cache.get('active', 0),
                'inactive': cls._user_cache.get('inactive', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'total': 0,
                'active': 0,
                'inactive': 0
            } 