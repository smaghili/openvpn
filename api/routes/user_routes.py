from flask import Blueprint, request, jsonify
from typing import Optional
from api.middleware.jwt_middleware import JWTMiddleware
from service.user_service import UserService
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager
from data.db import Database
from data.user_repository import UserRepository
from config.config import config

user_bp = Blueprint('users', __name__)

def get_user_service() -> UserService:
    """Factory function to create UserService with all dependencies."""
    db = Database()
    user_repo = UserRepository(db)
    login_manager = LoginUserManager()
    openvpn_manager = OpenVPNManager()
    return UserService(user_repo, openvpn_manager, login_manager)

@user_bp.route('/', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:create')
def create_user():
    """
    Create a new VPN user with optional password authentication.
    
    Request body:
    {
        "username": "string",
        "password": "string" (optional)
    }
    """
    data = request.get_json()
    
    if not data or 'username' not in data:
        return jsonify({
            'error': 'Missing required field',
            'message': 'Username is required'
        }), 400
    
    username = data['username'].strip()
    password = data.get('password', '').strip() or None
    
    validated_username = config.validate_username(username)
    
    # Get current admin info for user creation tracking
    from flask import g
    current_admin = getattr(g, 'current_admin', None)
    admin_id = current_admin['admin_id'] if current_admin else None
    
    user_service = get_user_service()
    config_data = user_service.create_user(validated_username, password)
    
    # Update user with creator info if admin_id available
    if admin_id and config_data:
        user_id = user_service.user_repo.get_user_id_by_username(validated_username)
        if user_id:
            query = "UPDATE users SET created_by = ? WHERE id = ?"
            user_service.user_repo.db.execute_query(query, (admin_id, user_id))
    
    response = {
        'message': f'User "{username}" created successfully',
        'username': username,
        'has_certificate': bool(config_data),
        'has_password': bool(password)
    }
    
    if config_data:
        response['certificate_config'] = config_data
    
    return jsonify(response), 201

@user_bp.route('/<username>', methods=['DELETE'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:delete')
def remove_user(username: str):
    """Remove a VPN user and all associated credentials."""
    user_service = get_user_service()
    user_service.remove_user(username, silent=True)
    
    return jsonify({
        'message': f'User "{username}" removed successfully',
        'username': username
    }), 200

@user_bp.route('/', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:read')
def list_users():
    """List VPN users with their status and usage information (filtered by admin access)."""
    from flask import g
    current_admin = g.current_admin
    
    user_service = get_user_service()
    users = user_service.get_all_users_with_status()
    
    # Filter users based on admin role
    if current_admin['role'] != 'admin':
        users = [user for user in users if user.get('created_by') == current_admin['admin_id']]
    
    if not users:
        return jsonify({
            'message': 'No users found',
            'users': []
        }), 200
    
    # Process users to group by username
    user_map = {}
    for user in users:
        username = user['username']
        if username not in user_map:
            user_map[username] = {
                'username': username,
                'status': user.get('status', 'active'),
                'quota_bytes': user.get('quota_bytes', 0),
                'bytes_used': user.get('bytes_used', 0),
                'auth_types': []
            }
        if user.get('auth_type'):
            user_map[username]['auth_types'].append(user['auth_type'])
    
    # Calculate usage percentage
    processed_users = []
    for username, data in user_map.items():
        quota = data['quota_bytes']
        used = data['bytes_used']
        
        user_data = {
            'username': username,
            'status': data['status'],
            'quota_bytes': quota,
            'bytes_used': used,
            'usage_percentage': round((used / quota) * 100, 1) if quota > 0 else None,
            'auth_types': data['auth_types']
        }
        processed_users.append(user_data)
    
    return jsonify({
        'message': f'Found {len(processed_users)} users',
        'users': processed_users
    }), 200

@user_bp.route('/stats', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:read')
def get_user_stats():
    """Get user statistics for dashboard"""
    try:
        user_service = get_user_service()
        
        total_users = user_service.get_total_user_count()
        online_users = user_service.get_online_user_count()
        total_usage = user_service.get_total_usage()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'online_users': online_users,
                'total_usage': total_usage
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get user stats: {str(e)}'
        }), 500

@user_bp.route('/<username>/config', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:read')
def get_user_config(username: str):
    """Get the OpenVPN configuration file for a specific user."""
    user_service = get_user_service()
    config = user_service.get_user_config(username)
    
    if not config:
        return jsonify({
            'error': 'Config not found',
            'message': f'No certificate-based config found for user "{username}"'
        }), 404
    
    return jsonify({
        'message': f'Config retrieved for user "{username}"',
        'username': username,
        'config': config
    }), 200

@user_bp.route('/shared-config', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:read')
def get_shared_config():
    """Get the shared OpenVPN configuration for username/password authentication."""
    user_service = get_user_service()
    config = user_service.get_shared_config()
    
    return jsonify({
        'message': 'Shared login-based config retrieved',
        'config': config
    }), 200

@user_bp.route('/<username>/password', methods=['PUT'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('users:update')
def change_user_password(username: str):
    """
    Change password for an existing user.
    
    Request body:
    {
        "new_password": "string"
    }
    """
    data = request.get_json()
    
    if not data or 'new_password' not in data:
        return jsonify({
            'error': 'Missing required field',
            'message': 'new_password is required'
        }), 400
    
    new_password = data['new_password']
    if not new_password or not new_password.strip():
        return jsonify({
            'error': 'Invalid password',
            'message': 'Password cannot be empty'
        }), 400
    
    user_service = get_user_service()
    user_service.change_user_password(username, new_password.strip())
    
    return jsonify({
        'message': f'Password changed successfully for user "{username}"',
        'username': username
    }), 200