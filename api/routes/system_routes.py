import os
import tempfile
from flask import Blueprint, request, jsonify, send_file
from api.middleware.jwt_middleware import JWTMiddleware
from service.user_service import UserService
from service.system_service import SystemService
from service.secure_storage_service import SecureStorageService
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
    secure_storage = SecureStorageService()
    
    backupable_components = [openvpn_manager, login_manager, user_service]
    backup_service = BackupService(backupable_components)
    
    return {
        'user_service': user_service,
        'openvpn_manager': openvpn_manager,
        'backup_service': backup_service,
        'secure_storage': secure_storage
    }

@system_bp.route('/backup/password/check', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def check_stored_password():
    """Check if current admin has a stored backup password."""
    try:
        from flask import g
        admin_id = g.current_admin['admin_id']
        
        services = get_services()
        secure_storage = services['secure_storage']
        
        has_password = secure_storage.has_stored_password(admin_id)
        
        return jsonify({
            'success': True,
            'has_stored_password': has_password
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@system_bp.route('/backup', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def create_backup():
    """
    Create an encrypted backup of the entire VPN system.
    
    Request body:
    {
        "password": "string" (optional if stored),
        "remember": "boolean" (optional),
        "use_stored": "boolean" (optional),
        "backup_dir": "string" (optional, defaults to ~/backups)
    }
    """
    from flask import g
    admin_id = g.current_admin['admin_id']
    
    data = request.get_json() or {}
    services = get_services()
    backup_service = services['backup_service']
    secure_storage = services['secure_storage']
    
    password = None
    use_stored = data.get('use_stored', False)
    remember = data.get('remember', False)
    
    # Try to use stored password if requested
    if use_stored:
        password = secure_storage.get_password(admin_id)
        if not password:
            return jsonify({
                'error': 'No stored password',
                'message': 'No stored backup password found for current user'
            }), 400
    else:
        # Use provided password
        password = data.get('password')
        if not password:
            return jsonify({
                'error': 'Missing required field',
                'message': 'Backup password is required'
            }), 400
        
        # Store password if remember is checked
        if remember:
            secure_storage.store_password(admin_id, password)
    
    backup_dir = data.get('backup_dir', '~/backups')
    
    try:
        backup_file = backup_service.create_backup(password, backup_dir)
        
        return jsonify({
            'message': 'Backup created successfully',
            'backup_file': backup_file,
            'backup_directory': os.path.expanduser(backup_dir),
            'download_url': f'/api/system/backup/download/{os.path.basename(backup_file)}'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Backup failed',
            'message': str(e)
        }), 500

@system_bp.route('/backup/download/<filename>', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def download_backup(filename):
    """Download a backup file."""
    try:
        backup_dir = os.path.expanduser('~/backups')
        backup_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_path):
            return jsonify({
                'error': 'File not found',
                'message': f'Backup file {filename} not found'
            }), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Download failed',
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

@system_bp.route('/stats', methods=['GET'])
@JWTMiddleware.require_auth
def get_system_stats():
    """Get real-time system statistics"""
    try:
        result = SystemService.get_system_stats()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@system_bp.route('/services', methods=['GET'])
@JWTMiddleware.require_auth
def get_service_status():
    """Get real-time service status"""
    try:
        # Check if this is a forced refresh
        force_refresh = request.args.get('force', 'false').lower() == 'true'
        if force_refresh:
            SystemService.clear_service_cache()
            
        result = SystemService.get_service_status()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@system_bp.route('/services/status', methods=['GET'])
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

@system_bp.route('/services/<service_name>/<action>', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('system:config')
def control_service(service_name, action):
    """Control system services (start, stop, restart)"""
    if action not in ['start', 'stop', 'restart']:
        return jsonify({
            'error': 'Invalid action',
            'message': 'Action must be start, stop, or restart'
        }), 400
    
    try:
        result = SystemService.control_service(service_name, action)
        return jsonify(result), 200 if result['success'] else 500
    except Exception as e:
        return jsonify({
            'error': 'Service control failed',
            'message': str(e)
        }), 500

@system_bp.route('/logs/<service_name>', methods=['GET'])
@JWTMiddleware.require_auth
def get_service_logs(service_name):
    """Get service logs"""
    lines = request.args.get('lines', 100, type=int)
    follow = request.args.get('follow', False, type=bool)
    
    try:
        result = SystemService.get_service_logs(service_name, lines, follow)
        return jsonify(result), 200 if result['success'] else 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to get logs',
            'message': str(e)
        }), 500

@system_bp.route('/logs/<service_name>/download', methods=['GET'])
@JWTMiddleware.require_auth
def download_service_logs(service_name):
    """Download service logs as file"""
    try:
        log_file = SystemService.get_log_file_path(service_name)
        if not log_file or not os.path.exists(log_file):
            return jsonify({
                'error': 'Log file not found',
                'message': f'No log file found for service {service_name}'
            }), 404
        
        return send_file(
            log_file,
            as_attachment=True,
            download_name=f"{service_name}_logs_{SystemService.get_timestamp()}.txt",
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({
            'error': 'Failed to download logs',
            'message': str(e)
        }), 500

@system_bp.route('/uptime', methods=['GET'])
@JWTMiddleware.require_auth
def get_system_uptime():
    """Get system uptime information"""
    try:
        result = SystemService.get_system_uptime()
        return jsonify(result), 200 if result['success'] else 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to get uptime',
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