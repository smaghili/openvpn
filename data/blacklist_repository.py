"""
Repository for managing JWT token blacklist with automatic cleanup.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .db import Database
from core.exceptions import DatabaseError

class BlacklistRepository:
    """
    Repository for managing JWT token blacklist with database persistence.
    """
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def blacklist_token(self, token_id: str, admin_id: int, expires_at: datetime) -> None:
        """
        Add token to blacklist with expiry timestamp.
        """
        query = """
        INSERT OR IGNORE INTO token_blacklist (token_id, admin_id, expires_at) 
        VALUES (?, ?, ?)
        """
        expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        self.db.execute_query(query, (token_id, admin_id, expires_str))
    
    def is_token_blacklisted(self, token_id: str) -> bool:
        """
        Check if token is blacklisted and not expired.
        """
        query = """
        SELECT 1 FROM token_blacklist 
        WHERE token_id = ? AND expires_at > datetime('now')
        """
        result = self.db.execute_query(query, (token_id,))
        return bool(result)
    
    def blacklist_all_admin_tokens(self, admin_id: int, expires_at: datetime) -> None:
        """
        Blacklist all tokens for specific admin (used when changing password).
        Note: This requires token IDs to be tracked separately.
        """
        expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        query = """
        INSERT OR IGNORE INTO token_blacklist (token_id, admin_id, expires_at)
        SELECT DISTINCT token_id, ?, ?
        FROM token_blacklist 
        WHERE admin_id = ? AND expires_at > datetime('now')
        """
        self.db.execute_query(query, (admin_id, expires_str, admin_id))
    
    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from blacklist and return count removed.
        """
        query = "DELETE FROM token_blacklist WHERE expires_at <= datetime('now')"
        result = self.db.execute_query(query)
        return result if isinstance(result, int) else 0
    
    def get_blacklisted_tokens(self, admin_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get blacklisted tokens with optional admin filter.
        """
        if admin_id:
            query = """
            SELECT token_id, admin_id, blacklisted_at, expires_at 
            FROM token_blacklist 
            WHERE admin_id = ? AND expires_at > datetime('now')
            ORDER BY blacklisted_at DESC 
            LIMIT ?
            """
            return self.db.execute_query(query, (admin_id, limit))
        else:
            query = """
            SELECT tb.token_id, tb.admin_id, tb.blacklisted_at, tb.expires_at, a.username
            FROM token_blacklist tb
            LEFT JOIN admins a ON tb.admin_id = a.id
            WHERE tb.expires_at > datetime('now')
            ORDER BY tb.blacklisted_at DESC 
            LIMIT ?
            """
            return self.db.execute_query(query, (limit,))
    
    def get_blacklist_stats(self) -> Dict[str, Any]:
        """
        Get blacklist statistics for monitoring.
        """
        stats_query = """
        SELECT 
            COUNT(*) as total_blacklisted,
            COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as active_blacklisted,
            COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as expired_blacklisted,
            MIN(blacklisted_at) as oldest_blacklisted,
            MAX(blacklisted_at) as newest_blacklisted
        FROM token_blacklist
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(stats_query)
            stats_row = cursor.fetchone()
            stats = dict(stats_row) if stats_row else {}

            admin_stats_query = """
            SELECT
                a.username,
                COUNT(tb.token_id) as blacklisted_count
            FROM token_blacklist tb
            JOIN admins a ON tb.admin_id = a.id
            WHERE tb.expires_at > datetime('now')
            GROUP BY a.id, a.username
            ORDER BY blacklisted_count DESC
            """
            cursor.execute(admin_stats_query)
            admin_stats = [dict(row) for row in cursor.fetchall()]

        return {
            'overall': stats,
            'by_admin': admin_stats
        }
    
    def bulk_cleanup(self, days_old: int = 7) -> int:
        """
        Remove tokens that expired more than specified days ago.
        """
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d %H:%M:%S')
        query = "DELETE FROM token_blacklist WHERE expires_at < ?"
        result = self.db.execute_query(query, (cutoff_date,))
        return result if isinstance(result, int) else 0