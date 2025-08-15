"""
Permission management routes for dynamic admin permission control.
"""

from flask import Blueprint, request, jsonify, g
from api.middleware.jwt_middleware import JWTMiddleware
from data.db import Database
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.user_repository import UserRepository
from service.admin_service import AdminService
from core.exceptions import AuthenticationError, ValidationError, UserNotFoundError

permission_bp = Blueprint('permissions', __name__)

def get_admin_service() -> AdminService:
    """Factory function to create AdminService with all dependencies."""
    db = Database()
    admin_repo = AdminRepository(db)
    permission_repo = PermissionRepository(db)
    user_repo = UserRepository(db)
    
    return AdminService(admin_repo, permission_repo, user_repo)

def get_permission_repo() -> PermissionRepository:
    """Factory function to create PermissionRepository."""
    db = Database()
    return PermissionRepository(db)

@permission_bp.route('/available', methods=['GET'])
@JWTMiddleware.require_auth
def get_available_permissions():
    """
    Get list of all available permissions in the system.
    """
    try:
        permission_repo = get_permission_repo()
        permissions = permission_repo.get_all_permissions()
        
        return jsonify({
            'permissions': permissions,
            'total': len(permissions)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving permissions',
            'message': 'Unable to fetch available permissions'
        }), 500

@permission_bp.route('/admins/<int:admin_id>', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:read')
def get_admin_permissions(admin_id):
    """
    Get permissions for specific admin user.
    """
    try:
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        permissions_data = admin_service.get_admin_permissions(admin_id, current_admin['admin_id'])
        
        return jsonify(permissions_data), 200
        
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
            'error': 'Error retrieving permissions',
            'message': 'Unable to fetch admin permissions'
        }), 500

@permission_bp.route('/admins/<int:admin_id>', methods=['POST'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('permissions:grant')
def grant_permissions(admin_id):
    """
    Grant permissions to admin user.
    
    Request body:
    {
        "permissions": ["permission1", "permission2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('permissions'):
            return jsonify({
                'error': 'Missing permissions data',
                'message': 'List of permissions is required'
            }), 400
        
        permissions = data['permissions']
        if not isinstance(permissions, list):
            return jsonify({
                'error': 'Invalid permissions format',
                'message': 'Permissions must be provided as a list'
            }), 400
        
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        result = admin_service.grant_permissions(admin_id, permissions, current_admin['admin_id'])
        
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
            'error': 'Permission grant error',
            'message': 'Unable to grant permissions'
        }), 500

@permission_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('permissions:revoke')
def revoke_permissions(admin_id):
    """
    Revoke permissions from admin user.
    
    Request body:
    {
        "permissions": ["permission1", "permission2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('permissions'):
            return jsonify({
                'error': 'Missing permissions data',
                'message': 'List of permissions to revoke is required'
            }), 400
        
        permissions = data['permissions']
        if not isinstance(permissions, list):
            return jsonify({
                'error': 'Invalid permissions format',
                'message': 'Permissions must be provided as a list'
            }), 400
        
        current_admin = g.current_admin
        admin_service = get_admin_service()
        
        result = admin_service.revoke_permissions(admin_id, permissions, current_admin['admin_id'])
        
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
            'error': 'Permission revoke error',
            'message': 'Unable to revoke permissions'
        }), 500

@permission_bp.route('/summary', methods=['GET'])
@JWTMiddleware.require_auth
@JWTMiddleware.require_permission('admins:read')
def get_permissions_summary():
    """
    Get summary of permissions across all admins.
    """
    try:
        permission_repo = get_permission_repo()
        summary = permission_repo.get_permission_summary()
        
        return jsonify({
            'summary': summary
        }), 200
        
    except AuthenticationError as e:
        return jsonify({
            'error': 'Permission denied',
            'message': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'error': 'Error retrieving summary',
            'message': 'Unable to fetch permissions summary'
        }), 500