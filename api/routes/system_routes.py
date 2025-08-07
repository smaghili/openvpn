import os
import tempfile
from flask import Blueprint, request, jsonify, send_file
from api.middleware.jwt_middleware import JWTMiddleware
from service.user_service import UserService
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from core.backup_service import BackupService
from data.db import Database
from data.user_repository import UserRepository

system_bp = Blueprint('system', __name__)

def get_services():
    """Factory function to create all required services."""
    db = Database()
    user_repo = UserRepository(db)
    login_manager = LoginUserManager()
    openvpn_manager = OpenVPNManager()
    user_service = UserService(user_repo, openvpn_manager, login_manager)
    
    backupable_components = [openvpn_manager, login_manager, user_service]
    backup_service = BackupService(backupable_components)
    
    return {
        'user_service': user_service,
        'openvpn_manager': openvpn_manager,
        'backup_service': backup_service
    }

@system_bp.route('/backup', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def create_backup():
    """
    Create an encrypted backup of the entire VPN system.
    
    Request body:
    {
        "password": "string",
        "backup_dir": "string" (optional, defaults to ~/backups)
    }
    """
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({
            'error': 'Missing required field',
            'message': 'Backup password is required'
        }), 400
    
    password = data['password']
    if not password:
        return jsonify({
            'error': 'Invalid password',
            'message': 'Backup password cannot be empty'
        }), 400
    
    backup_dir = data.get('backup_dir', '~/backups')
    
    services = get_services()
    backup_service = services['backup_service']
    
    try:
        backup_file = backup_service.create_backup(password, backup_dir)
        
        return jsonify({
            'message': 'Backup created successfully',
            'backup_file': backup_file,
            'backup_directory': os.path.expanduser(backup_dir)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Backup failed',
            'message': str(e)
        }), 500

@system_bp.route('/restore', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def restore_system():
    """
    Restore the VPN system from an encrypted backup file.
    
    Request body:
    {
        "backup_path": "string",
        "password": "string"
    }
    """
    data = request.get_json()
    
    if not data or 'backup_path' not in data or 'password' not in data:
        return jsonify({
            'error': 'Missing required fields',
            'message': 'Both backup_path and password are required'
        }), 400
    
    backup_path = data['backup_path']
    password = data['password']
    
    if not backup_path or not password:
        return jsonify({
            'error': 'Invalid input',
            'message': 'Backup path and password cannot be empty'
        }), 400
    
    services = get_services()
    backup_service = services['backup_service']
    
    try:
        # Handle URL downloads
        local_path = backup_path
        if backup_path.startswith(('http://', 'https://')):
            import urllib.request
            local_path = os.path.join(tempfile.gettempdir(), os.path.basename(backup_path))
            urllib.request.urlretrieve(backup_path, local_path)
        
        backup_service.restore_system(local_path, password)
        
        # Cleanup downloaded file
        if backup_path.startswith(('http://', 'https://')) and os.path.exists(local_path):
            os.remove(local_path)
        
        return jsonify({
            'message': 'System restore completed successfully',
            'backup_path': backup_path
        }), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid backup or password',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Restore failed',
            'message': str(e)
        }), 500

@system_bp.route('/uninstall', methods=['DELETE'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def uninstall_vpn():
    """
    Completely uninstall the OpenVPN system and remove all users.
    
    Request body:
    {
        "confirm": true
    }
    """
    data = request.get_json()
    
    if not data or not data.get('confirm'):
        return jsonify({
            'error': 'Confirmation required',
            'message': 'Set "confirm": true to proceed with uninstallation'
        }), 400
    
    services = get_services()
    user_service = services['user_service']
    openvpn_manager = services['openvpn_manager']
    
    try:
        # Get all users before removal
        users = user_service.get_all_users_with_status()
        unique_users = set(user['username'] for user in users) if users else set()
        
        # Remove all users
        for username in unique_users:
            user_service.remove_user(username, silent=True)
        
        # Uninstall OpenVPN
        openvpn_manager.uninstall_openvpn(silent=True)
        
        return jsonify({
            'message': 'OpenVPN system uninstalled successfully',
            'users_removed': len(unique_users),
            'removed_users': list(unique_users)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Uninstallation failed',
            'message': str(e)
        }), 500

@system_bp.route('/services', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('reports:view')
def get_system_services():
    """Get system services status."""
    try:
        services_status = {
            'openvpn': {
                'name': 'OpenVPN',
                'status': 'running' if os.path.exists('/var/run/openvpn/server.pid') else 'stopped',
                'enabled': True
            },
            'api': {
                'name': 'OpenVPN Manager API',
                'status': 'running',
                'enabled': True
            }
        }
        
        return jsonify({
            'message': 'System services retrieved successfully',
            'services': services_status
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get system services',
            'message': str(e)
        }), 500

@system_bp.route('/health', methods=['GET'])
def system_health():
    """Get system health status (no authentication required)."""
    try:
        return jsonify({
            'status': 'healthy',
            'message': 'OpenVPN Manager API is running',
            'timestamp': os.popen('date').read().strip()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': str(e)
        }), 500

@system_bp.route('/status', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('reports:view')
def system_status():
    """Get overall system status and statistics."""
    try:
        services = get_services()
        user_service = services['user_service']
        openvpn_manager = services['openvpn_manager']
        
        # Check if system is installed
        installed = os.path.exists(OpenVPNManager.SETTINGS_FILE)
        
        if not installed:
            return jsonify({
                'message': 'OpenVPN system not installed',
                'installed': False,
                'users_count': 0,
                'settings': None
            }), 200
        
        # Get user statistics
        users = user_service.get_all_users_with_status()
        unique_users = set(user['username'] for user in users) if users else set()
        
        # Get system settings
        settings = openvpn_manager.settings
        
        return jsonify({
            'message': 'System status retrieved successfully',
            'installed': True,
            'users_count': len(unique_users),
            'settings': {
                'public_ip': settings.get('public_ip'),
                'cert_port': settings.get('cert_port'),
                'cert_proto': settings.get('cert_proto'),
                'login_port': settings.get('login_port'),
                'login_proto': settings.get('login_proto'),
                'dns': settings.get('dns'),
                'cipher': settings.get('cipher')
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get system status',
            'message': str(e)
        }), 500