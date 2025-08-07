"""
JWT middleware for secure authentication with real-time permission checking.
"""

import os
from functools import wraps
from typing import Optional, Dict, Any
from flask import request, jsonify, g
from data.db import Database
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.blacklist_repository import BlacklistRepository
from service.auth_service import AuthService
from core.jwt_service import JWTService
from core.exceptions import AuthenticationError, ValidationError

class JWTMiddleware:
    """
    JWT authentication middleware with comprehensive security controls.
    """
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize JWT middleware with Flask app."""
        pass
    
    @staticmethod
    def require_auth(f):
        """Decorator to require JWT authentication for protected endpoints."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                auth_service = JWTMiddleware._get_auth_service()
                token = JWTMiddleware._extract_token(request)
                
                if not token:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'Please provide Authorization header with Bearer token'
                    }), 401
                
                admin_data = auth_service.verify_token(token)
                
                if not auth_service.check_admin_rate_limit(admin_data['admin_id']):
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please slow down.'
                    }), 429
                
                g.current_admin = admin_data
                g.auth_service = auth_service
                
                return f(*args, **kwargs)
                
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
                    'error': 'Authentication error',
                    'message': 'An unexpected error occurred during authentication'
                }), 500
        
        return decorated_function
    
    @staticmethod
    def require_permission(permission: str):
        """Decorator to require specific permission for endpoint access."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(g, 'current_admin'):
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'This endpoint requires authentication'
                    }), 401
                
                auth_service = g.get('auth_service')
                if not auth_service:
                    return jsonify({
                        'error': 'Authentication service unavailable',
                        'message': 'Unable to verify permissions'
                    }), 500
                
                admin_id = g.current_admin['admin_id']
                
                if not auth_service.check_permission(admin_id, permission):
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'This action requires "{permission}" permission'
                    }), 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    @staticmethod
    def require_any_permission(permissions: list):
        """Decorator to require any of the specified permissions."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(g, 'current_admin'):
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'This endpoint requires authentication'
                    }), 401
                
                auth_service = g.get('auth_service')
                if not auth_service:
                    return jsonify({
                        'error': 'Authentication service unavailable',
                        'message': 'Unable to verify permissions'
                    }), 500
                
                admin_id = g.current_admin['admin_id']
                
                has_permission = any(
                    auth_service.check_permission(admin_id, perm) 
                    for perm in permissions
                )
                
                if not has_permission:
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'This action requires one of: {", ".join(permissions)}'
                    }), 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    @staticmethod
    def optional_auth(f):
        """Decorator for endpoints that can work with or without authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                token = JWTMiddleware._extract_token(request)
                
                if token:
                    auth_service = JWTMiddleware._get_auth_service()
                    admin_data = auth_service.verify_token(token)
                    g.current_admin = admin_data
                    g.auth_service = auth_service
                else:
                    g.current_admin = None
                    g.auth_service = None
                
                return f(*args, **kwargs)
                
            except Exception:
                g.current_admin = None
                g.auth_service = None
                return f(*args, **kwargs)
        
        return decorated_function
    
    @staticmethod
    def _extract_token(request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]
    
    @staticmethod
    def _get_auth_service() -> AuthService:
        """Factory method to create AuthService with all dependencies."""
        db = Database()
        admin_repo = AdminRepository(db)
        permission_repo = PermissionRepository(db)
        blacklist_repo = BlacklistRepository(db)
        jwt_service = JWTService.create_service()
        
        return AuthService(admin_repo, permission_repo, blacklist_repo, jwt_service)
    
    @staticmethod
    def get_current_admin() -> Optional[Dict[str, Any]]:
        """Get current authenticated admin from Flask g object."""
        return getattr(g, 'current_admin', None)
    
    @staticmethod
    def get_auth_service() -> Optional[AuthService]:
        """Get auth service from Flask g object."""
        return getattr(g, 'auth_service', None)
    
    @staticmethod
    def check_user_access(user_id: int) -> bool:
        """Check if current admin has access to specific VPN user."""
        current_admin = JWTMiddleware.get_current_admin()
        if not current_admin:
            return False
        
        if current_admin['role'] == 'admin':
            return True
        
        try:
            from data.user_repository import UserRepository
            db = Database()
            user_repo = UserRepository(db)
            
            user = user_repo.get_user_by_id(user_id)
            if not user:
                return False
            
            return user.get('created_by') == current_admin['admin_id']
            
        except Exception:
            return False