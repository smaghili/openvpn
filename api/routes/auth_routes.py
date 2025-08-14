"""
Authentication routes for JWT-based login, logout, and token management.
"""

from flask import Blueprint, request, jsonify, g
from api.middleware.jwt_middleware import JWTMiddleware
from data.db import Database
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.blacklist_repository import BlacklistRepository
from service.auth_service import AuthService
from core.jwt_service import JWTService
from core.exceptions import AuthenticationError, ValidationError

auth_bp = Blueprint('auth', __name__)

def get_auth_service() -> AuthService:
    """Factory function to create AuthService with all dependencies."""
    db = Database()
    admin_repo = AdminRepository(db)
    permission_repo = PermissionRepository(db)
    blacklist_repo = BlacklistRepository(db)
    jwt_service = JWTService.create_service()
    
    return AuthService(admin_repo, permission_repo, blacklist_repo, jwt_service)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate admin user and return JWT token.
    
    Request body:
    {
        "username": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Missing credentials',
                'message': 'Username and password are required'
            }), 400
        
        username = data['username']
        password = data['password']
        client_ip = request.remote_addr
        
        auth_service = get_auth_service()
        result = auth_service.login(username, password, client_ip)
        
        return jsonify(result), 200
        
    except AuthenticationError as e:
        return jsonify({
            'error': 'Authentication failed',
            'message': str(e)
        }), 401
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Login error',
            'message': 'An unexpected error occurred during login'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@JWTMiddleware.require_auth
def logout():
    try:
        token = JWTMiddleware._extract_token(request)
        auth_service = g.auth_service
        result = auth_service.logout(token)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'error': 'Logout error',
            'message': 'An error occurred during logout'
        }), 500

@auth_bp.route('/verify', methods=['GET'])
@JWTMiddleware.require_auth
def verify_token():
    """
    Verify current JWT token validity and return user info.
    """
    try:
        admin_data = g.current_admin
        auth_service = g.auth_service
        
        permissions = auth_service.permission_repo.get_admin_permissions(admin_data['admin_id'])
        
        return jsonify({
            'valid': True,
            'admin': {
                'id': admin_data['admin_id'],
                'username': admin_data['username'],
                'role': admin_data['role']
            },
            'permissions': permissions
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Token verification error',
            'message': 'Unable to verify token'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@JWTMiddleware.require_auth
def refresh_token():
    """
    Refresh JWT token (blacklist current, issue new one).
    """
    try:
        current_token = JWTMiddleware._extract_token(request)
        admin_data = g.current_admin
        auth_service = g.auth_service
        
        auth_service.logout(current_token)
        
        admin = auth_service.admin_repo.get_admin_by_id(admin_data['admin_id'])
        if not admin:
            return jsonify({
                'error': 'Admin not found',
                'message': 'Admin account no longer exists'
            }), 404
        
        token_data = auth_service.jwt_service.generate_token(
            admin['id'],
            admin['username'],
            admin['role'],
            admin['token_version']
        )
        
        return jsonify({
            'token': token_data['token'],
            'expires_in': token_data['expires_in'],
            'message': 'Token refreshed successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Token refresh error',
            'message': 'Unable to refresh token'
        }), 500

@auth_bp.route('/change-password', methods=['PUT'])
@JWTMiddleware.require_auth
def change_password():
    """
    Change current admin's password.
    
    Request body:
    {
        "current_password": "string",
        "new_password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({
                'error': 'Missing password data',
                'message': 'Current password and new password are required'
            }), 400
        
        admin_data = g.current_admin
        auth_service = g.auth_service
        
        auth_service.change_password(
            admin_data['admin_id'],
            data['current_password'],
            data['new_password'],
            admin_data['admin_id']
        )
        
        return jsonify({
            'message': 'Password changed successfully. Please login again.'
        }), 200
        
    except AuthenticationError as e:
        return jsonify({
            'error': 'Authentication failed',
            'message': str(e)
        }), 401
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Password change error',
            'message': 'An error occurred while changing password'
        }), 500