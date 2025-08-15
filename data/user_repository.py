from typing import Optional, List, Dict, Any
from .db import Database
from core.types import Username, UserData, DatabaseResult
from core.exceptions import DatabaseError, UserNotFoundError
import hashlib
import os

class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._create_tables_if_not_exist()

    def _create_tables_if_not_exist(self) -> None:
        schema_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.sql')
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema = f.read()
            self.db.execute_script(schema)

    def add_user(self, username: Username, password_hash: Optional[str] = None) -> Optional[int]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row['id'] if row else None

    def add_user_protocol(self, user_id: int, protocol: str, auth_type: str, cert_pem: Optional[str] = None, key_pem: Optional[str] = None) -> None:
        query = """
        INSERT INTO user_protocols (user_id, protocol, auth_type, cert_pem, key_pem) 
        VALUES (?, ?, ?, ?, ?)
        """
        self.db.execute_query(query, (user_id, protocol, auth_type, cert_pem, key_pem))

    def get_user_by_username(self, username: Username, auth_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if auth_type:
            query = """
            SELECT u.*, up.protocol, up.auth_type, up.cert_pem, up.key_pem, up.status as protocol_status
            FROM users u
            LEFT JOIN user_protocols up ON u.id = up.user_id
            WHERE u.username = ? AND up.auth_type = ?
            """
            params = (username, auth_type)
            result = self.db.execute_query(query, params)
            return result[0] if result else None
        else:
            query = """
            SELECT u.*, up.protocol, up.auth_type, up.cert_pem, up.key_pem, up.status as protocol_status
            FROM users u
            LEFT JOIN user_protocols up ON u.id = up.user_id
            WHERE u.username = ?
            """
            params = (username,)
            # This was returning a list, changed to return one item
            result = self.db.execute_query(query, params)
            return result[0] if result else None
    
    def find_user_by_username(self, username: Username) -> Optional[Dict[str, Any]]:
        """Finds a user by username from the users table only."""
        query = "SELECT * FROM users WHERE username = ?"
        result = self.db.execute_query(query, (username,))
        return result[0] if result else None

    def get_all_users_with_details(self) -> List[Dict[str, Any]]:
        """Retrieves all users with their protocol and quota information."""
        query = """
        SELECT 
            u.id,
            u.username, 
            u.status, 
            u.created_at, 
            up.auth_type, 
            up.protocol,
            uq.quota_bytes,
            uq.bytes_used
        FROM users u
        LEFT JOIN user_protocols up ON u.id = up.user_id
        LEFT JOIN user_quotas uq ON u.id = uq.user_id
        ORDER BY u.username, up.auth_type
        """
        return self.db.execute_query(query)

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieves all users from the users table."""
        query = "SELECT * FROM users ORDER BY username"
        return self.db.execute_query(query)

    def remove_user(self, username: Username) -> None:
        query = "DELETE FROM users WHERE username = ?"
        self.db.execute_query(query, (username,))

    def update_user_password(self, username: Username, password_hash: str) -> None:
        """Updates the password hash for an existing user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
            if cursor.rowcount == 0:
                raise UserNotFoundError(username)

    # --- New methods for quota management ---

    def set_user_quota(self, user_id: int, quota_gb: float) -> None:
        """Sets or updates the data quota for a user in bytes."""
        quota_bytes = int(quota_gb * 1024 * 1024 * 1024)
        query = """
        INSERT INTO user_quotas (user_id, quota_bytes) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET quota_bytes = excluded.quota_bytes;
        """
        self.db.execute_query(query, (user_id, quota_bytes))

    def get_total_user_count(self) -> int:
        """Get total number of users"""
        query = "SELECT COUNT(DISTINCT username) as total FROM users WHERE status = 'active'"
        result = self.db.execute_query(query)
        return result[0]['total'] if result else 0

    def get_online_user_count(self) -> int:
        """Get number of currently online users (estimate based on recent activity)"""
        query = """
        SELECT COUNT(DISTINCT user_id) as online 
        FROM traffic_logs 
        WHERE datetime(log_timestamp) > datetime('now', '-15 minutes')
        """
        result = self.db.execute_query(query)
        return result[0]['online'] if result else 0

    def get_total_usage(self) -> int:
        """Get total data usage across all users in bytes"""
        query = "SELECT COALESCE(SUM(bytes_used), 0) as total_usage FROM user_quotas"
        result = self.db.execute_query(query)
        return result[0]['total_usage'] if result else 0

    def get_user_quota_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a user's quota and current usage."""
        query = """
        SELECT u.username, q.quota_bytes, q.bytes_used
        FROM user_quotas q
        JOIN users u ON u.id = q.user_id
        WHERE q.user_id = ?
        """
        result = self.db.execute_query(query, (user_id,))
        return result[0] if result else None

    def update_user_traffic(self, username: str, bytes_sent: int, bytes_received: int) -> bool:
        """Updates user traffic usage and logs the session."""
        try:
            # Get user ID
            user = self.find_user_by_username(username)
            if not user:
                return False
                
            user_id = user['id']
            total_bytes = bytes_sent + bytes_received
            
            if total_bytes <= 0:
                return True  # No traffic to record
            
            # Use a shared connection for atomicity
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_quotas SET bytes_used = bytes_used + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (total_bytes, user_id)
                )
                cursor.execute(
                    "INSERT INTO traffic_logs (user_id, bytes_sent, bytes_received, log_timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                    (user_id, bytes_sent, bytes_received)
                )
                return True

        except Exception:
            return False

    def get_user_id_by_username(self, username: str) -> Optional[int]:
        """Get user ID by username."""
        user = self.find_user_by_username(username)
        return user['id'] if user else None

    def get_traffic_summary(self) -> List[Dict[str, Any]]:
        """Get traffic summary for all users for dashboard display."""
        query = """
        SELECT 
            u.username,
            u.status,
            uq.quota_bytes,
            uq.bytes_used,
            uq.updated_at as quota_updated,
            COALESCE(SUM(tl.bytes_sent), 0) as total_sent,
            COALESCE(SUM(tl.bytes_received), 0) as total_received,
            COUNT(tl.id) as session_count,
            MAX(tl.log_timestamp) as last_activity
        FROM users u
        LEFT JOIN user_quotas uq ON u.id = uq.user_id
        LEFT JOIN traffic_logs tl ON u.id = tl.user_id
        WHERE u.status = 'active'
        GROUP BY u.id, u.username, u.status, uq.quota_bytes, uq.bytes_used, uq.updated_at
        ORDER BY uq.bytes_used DESC
        """
        return self.db.execute_query(query)

    def get_recent_traffic_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent traffic logs for monitoring."""
        query = """
        SELECT 
            tl.log_timestamp,
            u.username,
            tl.bytes_sent,
            tl.bytes_received,
            (tl.bytes_sent + tl.bytes_received) as total_bytes
        FROM traffic_logs tl
        JOIN users u ON tl.user_id = u.id
        ORDER BY tl.log_timestamp DESC
        LIMIT ?
        """
        return self.db.execute_query(query, (limit,))
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = ?"
        result = self.db.execute_query(query, (user_id,))
        return result[0] if result else None
