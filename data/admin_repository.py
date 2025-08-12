"""
Repository for admin user management in the JWT authentication system.
"""

from typing import Optional, List, Dict, Any
from .db import Database
from core.exceptions import DatabaseError, UserNotFoundError, UserAlreadyExistsError
import bcrypt

class AdminRepository:
    """
    Repository for managing admin users with secure password handling.
    """
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def create_admin(self, username: str, password: str, role: str = 'reseller') -> int:
        """
        Create new admin user with encrypted password.
        """
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO admins (username, password_hash, role)
                    VALUES (?, ?, ?)
                    """,
                    (username, password_hash, role),
                )

                cursor.execute("SELECT id FROM admins WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    raise DatabaseError("Failed to create admin user")

                return row['id']

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise UserAlreadyExistsError(username)
            raise DatabaseError(f"Failed to create admin: {str(e)}")
    
    def get_admin_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve admin by username with all details.
        """
        query = "SELECT * FROM admins WHERE username = ?"
        result = self.db.execute_query(query, (username,))
        return result[0] if result else None
    
    def get_admin_by_id(self, admin_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve admin by ID with all details.
        """
        query = "SELECT * FROM admins WHERE id = ?"
        result = self.db.execute_query(query, (admin_id,))
        return result[0] if result else None
    
    def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify admin password and return admin data if valid.
        """
        admin = self.get_admin_by_username(username)
        if not admin:
            return None
        
        try:
            password_hash = admin['password_hash'].encode('utf-8')
            provided_password = password.encode('utf-8')
            
            if bcrypt.checkpw(provided_password, password_hash):
                return admin
            
        except Exception:
            pass
        
        return None
    
    def update_password(self, admin_id: int, new_password: str) -> None:
        """
        Update admin password and increment token version.
        """
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE admins
                    SET password_hash = ?, token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (password_hash, admin_id),
                )
                if cursor.rowcount == 0:
                    raise UserNotFoundError(f"Admin ID {admin_id}")

        except Exception as e:
            if isinstance(e, UserNotFoundError):
                raise e
            raise DatabaseError(f"Failed to update password: {str(e)}")
    
    def increment_token_version(self, admin_id: int) -> None:
        """
        Increment token version to invalidate all existing tokens.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admins SET token_version = token_version + 1 WHERE id = ?", (admin_id,))
            if cursor.rowcount == 0:
                raise UserNotFoundError(f"Admin ID {admin_id}")
    
    def get_all_admins(self) -> List[Dict[str, Any]]:
        """
        Retrieve all admins without password hashes for security.
        """
        query = """
        SELECT id, username, role, token_version, created_at, updated_at 
        FROM admins 
        ORDER BY created_at DESC
        """
        return self.db.execute_query(query)
    
    def update_admin(self, admin_id: int, updates: Dict[str, Any]) -> None:
        """
        Update admin details (excluding password).
        """
        allowed_fields = {'role'}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return
        
        set_clause = ", ".join([f"{field} = ?" for field in filtered_updates.keys()])
        query = f"UPDATE admins SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        values = list(filtered_updates.values()) + [admin_id]
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            if cursor.rowcount == 0:
                raise UserNotFoundError(f"Admin ID {admin_id}")
    
    def delete_admin(self, admin_id: int) -> None:
        """
        Delete admin user and all related data.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
            if cursor.rowcount == 0:
                raise UserNotFoundError(f"Admin ID {admin_id}")
    
    def get_admin_count(self) -> int:
        """
        Get total number of admin users.
        """
        query = "SELECT COUNT(*) as count FROM admins"
        result = self.db.execute_query(query)
        return result[0]['count'] if result else 0