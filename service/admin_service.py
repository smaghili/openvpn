"""
Admin management service with permission-based access control.
"""

from typing import List, Dict, Any, Optional
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.user_repository import UserRepository
from core.exceptions import AuthenticationError, ValidationError, UserAlreadyExistsError, UserNotFoundError
import re

class AdminService:
    """
    Service for managing admin users with role-based access control.
    """
    
    def __init__(self, admin_repo: AdminRepository, permission_repo: PermissionRepository, user_repo: UserRepository):
        self.admin_repo = admin_repo
        self.permission_repo = permission_repo
        self.user_repo = user_repo
    
    def create_admin(self, username: str, password: str, role: str, by_admin_id: int) -> Dict[str, Any]:
        """
        Create new admin user with permission validation.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:create'):
            raise AuthenticationError("Insufficient permissions to create admin")
        
        username, password = self._validate_admin_data(username, password, role)
        
        try:
            admin_id = self.admin_repo.create_admin(username, password, role)
            self.permission_repo.set_default_permissions(admin_id, role)
            
            return {
                'id': admin_id,
                'username': username,
                'role': role,
                'message': f'Admin "{username}" created successfully'
            }
            
        except UserAlreadyExistsError:
            raise ValidationError(f'Admin username "{username}" already exists')
    
    def get_admin(self, admin_id: int, by_admin_id: int) -> Dict[str, Any]:
        """
        Get admin details with permission checking.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:read'):
            raise AuthenticationError("Insufficient permissions to view admin details")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        permissions = self.permission_repo.get_admin_permissions(admin_id)
        
        return {
            'id': admin['id'],
            'username': admin['username'],
            'role': admin['role'],
            'token_version': admin['token_version'],
            'created_at': admin['created_at'],
            'updated_at': admin['updated_at'],
            'permissions': permissions
        }
    
    def get_all_admins(self, by_admin_id: int) -> List[Dict[str, Any]]:
        """
        Get all admin users with their permissions.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:read'):
            raise AuthenticationError("Insufficient permissions to view admins")
        
        admins = self.admin_repo.get_all_admins()
        
        for admin in admins:
            admin['permissions'] = self.permission_repo.get_admin_permissions(admin['id'])
        
        return admins
    
    def update_admin(self, admin_id: int, updates: Dict[str, Any], by_admin_id: int) -> Dict[str, Any]:
        """
        Update admin details with permission validation.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:update'):
            raise AuthenticationError("Insufficient permissions to update admin")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        allowed_updates = {}
        if 'role' in updates:
            role = str(updates['role']).strip().lower()
            if role not in ['admin', 'reseller']:
                raise ValidationError("Role must be 'admin' or 'reseller'")
            allowed_updates['role'] = role
        
        if allowed_updates:
            self.admin_repo.update_admin(admin_id, allowed_updates)
            
            if 'role' in allowed_updates:
                self.permission_repo.clear_admin_permissions(admin_id)
                self.permission_repo.set_default_permissions(admin_id, allowed_updates['role'])
        
        return {'message': 'Admin updated successfully'}
    
    def delete_admin(self, admin_id: int, by_admin_id: int) -> Dict[str, Any]:
        """
        Delete admin user with safety checks.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:delete'):
            raise AuthenticationError("Insufficient permissions to delete admin")
        
        if admin_id == by_admin_id:
            raise ValidationError("Cannot delete your own admin account")
        
        admin_count = self.admin_repo.get_admin_count()
        if admin_count <= 1:
            raise ValidationError("Cannot delete the last admin user")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        self.admin_repo.delete_admin(admin_id)
        
        return {'message': f'Admin "{admin["username"]}" deleted successfully'}
    
    def grant_permissions(self, admin_id: int, permissions: List[str], by_admin_id: int) -> Dict[str, Any]:
        """
        Grant permissions to admin user.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'permissions:grant'):
            raise AuthenticationError("Insufficient permissions to grant permissions")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        available_permissions = self.permission_repo.get_all_permissions()
        invalid_permissions = [p for p in permissions if p not in available_permissions]
        
        if invalid_permissions:
            raise ValidationError(f"Invalid permissions: {', '.join(invalid_permissions)}")
        
        self.permission_repo.grant_permissions(admin_id, permissions)
        
        return {
            'message': f'Granted {len(permissions)} permissions to {admin["username"]}',
            'granted_permissions': permissions
        }
    
    def revoke_permissions(self, admin_id: int, permissions: List[str], by_admin_id: int) -> Dict[str, Any]:
        """
        Revoke permissions from admin user.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'permissions:revoke'):
            raise AuthenticationError("Insufficient permissions to revoke permissions")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        self.permission_repo.revoke_permissions(admin_id, permissions)
        
        return {
            'message': f'Revoked {len(permissions)} permissions from {admin["username"]}',
            'revoked_permissions': permissions
        }
    
    def get_admin_permissions(self, admin_id: int, by_admin_id: int) -> Dict[str, Any]:
        """
        Get admin permissions with details.
        """
        if not self.permission_repo.has_permission(by_admin_id, 'admins:read'):
            raise AuthenticationError("Insufficient permissions to view permissions")
        
        admin = self.admin_repo.get_admin_by_id(admin_id)
        if not admin:
            raise UserNotFoundError(f"Admin ID {admin_id}")
        
        permissions = self.permission_repo.get_admin_permissions_with_details(admin_id)
        available_permissions = self.permission_repo.get_all_permissions()
        
        return {
            'admin': {
                'id': admin['id'],
                'username': admin['username'],
                'role': admin['role']
            },
            'permissions': permissions,
            'available_permissions': available_permissions
        }
    
    def has_access_to_user(self, admin_id: int, admin_role: str, vpn_user_id: int) -> bool:
        """
        Check if admin can access specific VPN user based on role.
        """
        if admin_role == 'admin':
            return True
        
        user = self.user_repo.get_user_by_id(vpn_user_id)
        if not user:
            return False
        
        return user.get('created_by') == admin_id
    
    def get_accessible_users(self, admin_id: int, admin_role: str) -> List[Dict[str, Any]]:
        """
        Get VPN users accessible to admin based on role.
        """
        all_users = self.user_repo.get_all_users_with_details()
        
        if admin_role == 'admin':
            return all_users
        
        return [user for user in all_users if user.get('created_by') == admin_id]
    
    def _validate_admin_data(self, username: str, password: str, role: str) -> tuple:
        """
        Validate admin creation data.
        """
        username = str(username).strip()[:50] if username else ""
        password = str(password)[:100] if password else ""
        role = str(role).strip().lower() if role else ""
        
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        if len(username) < 3 or len(username) > 50:
            raise ValidationError("Username must be 3-50 characters")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username contains invalid characters")
        
        if role not in ['admin', 'reseller']:
            raise ValidationError("Role must be 'admin' or 'reseller'")
        
        return username, password