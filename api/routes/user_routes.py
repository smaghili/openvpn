from flask import Blueprint, request, jsonify
from typing import Optional
from api.middleware.auth_middleware import AuthMiddleware
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
@AuthMiddleware.require_auth
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
    
    user_service = get_user_service()
    config_data = user_service.create_user(validated_username, password)
    
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
@AuthMiddleware.require_auth
def remove_user(username: str):
    """Remove a VPN user and all associated credentials."""
    user_service = get_user_service()
    user_service.remove_user(username, silent=True)
    
    return jsonify({
        'message': f'User "{username}" removed successfully',
        'username': username
    }), 200

@user_bp.route('/', methods=['GET'])
@AuthMiddleware.require_auth
def list_users():
    """List all VPN users with their status and usage information."""
    user_service = get_user_service()
    users = user_service.get_all_users_with_status()
    
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

@user_bp.route('/<username>/config', methods=['GET'])
@AuthMiddleware.require_auth
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
@AuthMiddleware.require_auth
def get_shared_config():
    """Get the shared OpenVPN configuration for username/password authentication."""
    user_service = get_user_service()
    config = user_service.get_shared_config()
    
    return jsonify({
        'message': 'Shared login-based config retrieved',
        'config': config
    }), 200

@user_bp.route('/<username>/password', methods=['PUT'])
@AuthMiddleware.require_auth
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