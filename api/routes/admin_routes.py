"""
Admin management routes for user administration and permission control.
"""

from flask import Blueprint, request, jsonify, g
from api.middleware.jwt_middleware import JWTMiddleware
from data.db import Database
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.user_repository import UserRepository
from service.admin_service import AdminService
from service.auth_service import AuthService
from core.exceptions import AuthenticationError, ValidationError, UserNotFoundError

admin_bp = Blueprint('admins', __name__)

def get_admin_service() -> AdminService:
    """Factory function to create AdminService with all dependencies."""
    db = Database()
    admin_repo = AdminRepository(db)
    permission_repo = PermissionRepository(db)
    user_repo = UserRepository(db)
    
    return AdminService(admin_repo, permission_repo, user_repo)

@admin_bp.route('/', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:read')
def get_all_admins():
    """
    Get list of all admin users with their permissions.
    """
    try:
        admin_data = g.current_admin
        admin_service = get_admin_service()
        
        admins = admin_service.get_all_admins(admin_data['admin_id'])
        
        return jsonify({
            'admins': admins,
            'total': len(admins)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving admins',
            'message': 'Unable to fetch admin list'
        }), 500

@admin_bp.route('/', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:create')
def create_admin():
    """
    Create new admin user.
    
    Request body:
    {
        "username": "string",
        "password": "string",
        "role": "admin" | "reseller"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Missing request data',
                'message': 'Request body is required'
            }), 400
        
        required_fields = ['username', 'password', 'role']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'message': f'Required fields: {", ".join(missing_fields)}'
            }), 400
        
        admin_data = g.current_admin
        admin_service = get_admin_service()
        
        result = admin_service.create_admin(
            data['username'],
            data['password'],
            data['role'],
            admin_data['admin_id']
        )
        
        return jsonify(result), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Admin creation error',
            'message': 'Unable to create admin user'
        }), 500

@admin_bp.route('/<int:admin_id>', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:read')
def get_admin(admin_id):
    """
    Get specific admin user details.
    """
    try:
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        admin_details = admin_service.get_admin(admin_id, current_admin['admin_id'])
        
        return jsonify(admin_details), 200
        
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Admin not found',
            'message': str(e)
        }), 404
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving admin',
            'message': 'Unable to fetch admin details'
        }), 500

@admin_bp.route('/<int:admin_id>', methods=['PUT'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:update')
def update_admin(admin_id):
    """
    Update admin user details.
    
    Request body:
    {
        "role": "admin" | "reseller"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Missing request data',
                'message': 'Request body is required'
            }), 400
        
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        result = admin_service.update_admin(admin_id, data, current_admin['admin_id'])
        
        return jsonify(result), 200
        
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Admin not found',
            'message': str(e)
        }), 404
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Admin update error',
            'message': 'Unable to update admin'
        }), 500

@admin_bp.route('/<int:admin_id>', methods=['DELETE'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:delete')
def delete_admin(admin_id):
    """
    Delete admin user.
    """
    try:
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        result = admin_service.delete_admin(admin_id, current_admin['admin_id'])
        
        return jsonify(result), 200
        
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Admin not found',
            'message': str(e)
        }), 404
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Admin deletion error',
            'message': 'Unable to delete admin'
        }), 500

@admin_bp.route('/<int:admin_id>/logout', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('tokens:revoke')
def force_logout_admin(admin_id):
    """
    Force logout admin by invalidating all their tokens.
    """
    try:
        current_admin = g.current_admin
        auth_service = g.auth_service
        
        logout_result = auth_service.force_logout_admin(admin_id, current_admin['admin_id'])
        
        return jsonify(logout_result), 200
        
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Admin not found',
            'message': str(e)
        }), 404
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Force logout error',
            'message': 'Unable to revoke admin sessions'
        }), 500

@admin_bp.route('/<int:admin_id>/password', methods=['PUT'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:update')
def change_admin_password(admin_id):
    """
    Change another admin's password (admin only).
    
    Request body:
    {
        "new_password": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('new_password'):
            return jsonify({
                'error': 'Missing password',
                'message': 'New password is required'
            }), 400
        
        current_admin = g.current_admin
        auth_service = g.auth_service
        
        auth_service.change_password(
            admin_id,
            '',  # Current password not required for admin changing other's password
            data['new_password'],
            current_admin['admin_id']
        )
        
        return jsonify({
            'message': 'Admin password changed successfully'
        }), 200
        
    except UserNotFoundError as e:
        return jsonify({
            'error': 'Admin not found',
            'message': str(e)
        }), 404
    except ValidationError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Password change error',
            'message': 'Unable to change admin password'
        }), 500