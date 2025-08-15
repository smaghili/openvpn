"""
Repository for managing admin permissions in the JWT authentication system.
"""

from typing import List, Dict, Any, Set
from .db import Database
from core.exceptions import DatabaseError, UserNotFoundError

class PermissionRepository:
    """
    Repository for managing dynamic admin permissions with real-time checking.
    """
    
    AVAILABLE_PERMISSIONS = [
        'users:create', 'users:read', 'users:update', 'users:delete',
        'admins:create', 'admins:read', 'admins:update', 'admins:delete',
        'permissions:grant', 'permissions:revoke',
        'system:config', 'quota:manage', 'reports:view',
        'profile:generate', 'profile:revoke', 'tokens:revoke'
    ]
    
    DEFAULT_PERMISSIONS = {
        'admin': AVAILABLE_PERMISSIONS,
        'reseller': [
            'users:create', 'users:read', 'users:update', 'users:delete',
            'quota:manage', 'reports:view', 'profile:generate', 'profile:revoke'
        ]
    }
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def grant_permission(self, admin_id: int, permission: str) -> None:
        """
        Grant permission to admin user.
        """
        if permission not in self.AVAILABLE_PERMISSIONS:
            raise DatabaseError(f"Invalid permission: {permission}")
        
        query = """
        INSERT OR IGNORE INTO admin_permissions (admin_id, permission) 
        VALUES (?, ?)
        """
        self.db.execute_query(query, (admin_id, permission))
    
    def revoke_permission(self, admin_id: int, permission: str) -> None:
        """
        Revoke permission from admin user.
        """
        query = "DELETE FROM admin_permissions WHERE admin_id = ? AND permission = ?"
        self.db.execute_query(query, (admin_id, permission))
    
    def grant_permissions(self, admin_id: int, permissions: List[str]) -> None:
        """
        Grant multiple permissions to admin user.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                for permission in permissions:
                    if permission not in self.AVAILABLE_PERMISSIONS:
                        raise DatabaseError(f"Invalid permission: {permission}")

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO admin_permissions (admin_id, permission)
                        VALUES (?, ?)
                        """,
                        (admin_id, permission),
                    )
        except Exception as e:
            raise DatabaseError(f"Failed to grant permissions: {str(e)}")
    
    def revoke_permissions(self, admin_id: int, permissions: List[str]) -> None:
        """
        Revoke multiple permissions from admin user.
        """
        if not permissions:
            return
        
        placeholders = ','.join(['?' for _ in permissions])
        query = f"DELETE FROM admin_permissions WHERE admin_id = ? AND permission IN ({placeholders})"
        self.db.execute_query(query, [admin_id] + permissions)
    
    def get_admin_permissions(self, admin_id: int) -> List[str]:
        """
        Get all permissions for admin user.
        """
        query = "SELECT permission FROM admin_permissions WHERE admin_id = ?"
        result = self.db.execute_query(query, (admin_id,))
        return [row['permission'] for row in result]
    
    def has_permission(self, admin_id: int, permission: str) -> bool:
        """
        Check if admin has specific permission (real-time database check).
        """
        query = "SELECT 1 FROM admin_permissions WHERE admin_id = ? AND permission = ?"
        result = self.db.execute_query(query, (admin_id, permission))
        return bool(result)
    
    def has_any_permission(self, admin_id: int, permissions: List[str]) -> bool:
        """
        Check if admin has any of the specified permissions.
        """
        if not permissions:
            return False
        
        placeholders = ','.join(['?' for _ in permissions])
        query = f"SELECT 1 FROM admin_permissions WHERE admin_id = ? AND permission IN ({placeholders})"
        result = self.db.execute_query(query, [admin_id] + permissions)
        return bool(result)
    
    def set_default_permissions(self, admin_id: int, role: str) -> None:
        """
        Set default permissions based on admin role.
        """
        default_perms = self.DEFAULT_PERMISSIONS.get(role, [])
        if default_perms:
            self.grant_permissions(admin_id, default_perms)
    
    def get_all_permissions(self) -> List[str]:
        """
        Get list of all available permissions.
        """
        return self.AVAILABLE_PERMISSIONS.copy()
    
    def get_admin_permissions_with_details(self, admin_id: int) -> List[Dict[str, Any]]:
        """
        Get admin permissions with grant timestamps.
        """
        query = """
        SELECT permission, granted_at 
        FROM admin_permissions 
        WHERE admin_id = ? 
        ORDER BY granted_at DESC
        """
        return self.db.execute_query(query, (admin_id,))
    
    def clear_admin_permissions(self, admin_id: int) -> None:
        """
        Remove all permissions from admin user.
        """
        query = "DELETE FROM admin_permissions WHERE admin_id = ?"
        self.db.execute_query(query, (admin_id,))
    
    def get_permission_summary(self) -> Dict[str, Any]:
        """
        Get summary of permissions across all admins.
        """
        query = """
        SELECT 
            a.username,
            a.role,
            GROUP_CONCAT(ap.permission) as permissions,
            COUNT(ap.permission) as permission_count
        FROM admins a
        LEFT JOIN admin_permissions ap ON a.id = ap.admin_id
        GROUP BY a.id, a.username, a.role
        ORDER BY a.username
        """
        result = self.db.execute_query(query)
        
        for row in result:
            if row['permissions']:
                row['permissions'] = row['permissions'].split(',')
            else:
                row['permissions'] = []
        
        return result