import psutil
import os
import time
from typing import Dict, Any
from data.db import Database
from data.user_repository import UserRepository

class SystemService:
    _last_cpu_times = None
    _last_cpu_check = 0
    _cpu_cache_duration = 3  # Cache CPU for 3 seconds
    _service_cache = None
    _service_cache_time = 0
    _service_cache_duration = 15  # Cache services for 15 seconds
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
            
            # Use cache if available and fresh
            if (cls._service_cache and 
                current_time - cls._service_cache_time < cls._service_cache_duration):
                return cls._service_cache
            
            # Check actual service status (lightweight checks)
            services = {
                'uds': cls._check_uds_status(),
                'wireguard': cls._check_wireguard_status(),
                'login': {'status': 'up', 'uptime': 'Active'},
                'cert': {'status': 'up', 'uptime': 'Active'}
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
            result = os.popen('systemctl is-active openvpn-uds-monitor 2>/dev/null').read().strip() 
            if result == 'active':
                log_check = os.popen('systemctl status openvpn-uds-monitor --lines=10 2>/dev/null | grep -c "ERROR"').read().strip()
                if log_check and int(log_check) > 0:
                    return {'status': 'error', 'uptime': 'Running with errors'}
                else:
                    return {'status': 'up', 'uptime': 'Active'}
            elif result == 'inactive':
                return {'status': 'down', 'uptime': 'Stopped'}
            else:
                return {'status': 'error', 'uptime': 'Error state'}
        except:
            return {'status': 'unknown', 'uptime': 'Unknown'}
    

    @staticmethod
    def _check_wireguard_status() -> Dict[str, str]:
        """Check WireGuard service status"""
        try:
            # Check WireGuard interface
            result = os.popen('wg show 2>/dev/null').read().strip()
            if result:
                return {'status': 'up', 'uptime': 'Active'}
            else:
                return {'status': 'down', 'uptime': 'Stopped'}
        except:
            return {'status': 'down', 'uptime': 'Stopped'}
    
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
            print(f"Error getting user count: {e}")
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
            print(f"Error getting user stats: {e}")
            return {
                'total': 0,
                'active': 0,
                'inactive': 0
            } 