import sqlite3
import os
from typing import List, Dict, Any, Tuple, Optional
from core.types import DatabaseResult, DatabaseRow
from core.exceptions import DatabaseError
from config.env_loader import get_config_value

# Use VPNPaths for consistent path management
from config.paths import VPNPaths

DATABASE_DIR = VPNPaths.get_database_dir()
# Check for environment variable first, then fall back to VPNPaths
DATABASE_FILE = os.environ.get('DATABASE_PATH', VPNPaths.get_database_file())

class Database:
    """
    Handles all low-level interactions with the SQLite database.
    """
    def __init__(self, db_file: str = DATABASE_FILE) -> None:
        """
        Initializes the database connection.

        Args:
            db_file (str): The path to the SQLite database file.
        """
        self.db_file = db_file
        # Ensure the directory for the database exists before connecting.
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establishes a connection to the database."""
        try:
            # The check_same_thread=False is important for applications
            # where different threads might interact with the database.
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def disconnect(self) -> None:
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str, params: Tuple = ()) -> DatabaseResult:
        """
        Executes a given SQL query (e.g., SELECT, INSERT, UPDATE, DELETE).
        For queries that modify data, this method handles commit and rollback.

        Args:
            query (str): The SQL query to execute.
            params (tuple): The parameters to substitute into the query.

        Returns:
            list: A list of rows for SELECT queries, otherwise an empty list.
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                result: DatabaseResult = [dict(row) for row in cursor.fetchall()]
                return result
            else:
                self.conn.commit()
                return []
        except sqlite3.Error as e:
            if self.conn:
                self.conn.rollback()
            raise DatabaseError(f"Database query failed: {e}")
        finally:
            self.disconnect()

    def execute_script(self, script: str) -> None:
        """
        Executes a multi-statement SQL script.

        Args:
            script (str): The SQL script to execute.
        """
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.executescript(script)
            self.conn.commit()
        except sqlite3.Error as e:
            if self.conn:
                self.conn.rollback()
            raise DatabaseError(f"Database script execution failed: {e}")
        finally:
            self.disconnect()

    def get_connection(self):
        """
        Returns a context manager for database connections.
        This allows for better connection management in UDS monitor.
        """
        class ConnectionContext:
            def __init__(self, db_instance):
                self.db = db_instance
                self.conn = None
            
            def __enter__(self):
                self.db.connect()
                self.conn = self.db.conn
                return self.conn
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.conn:
                    self.conn.close()
                    self.conn = None
                self.db.conn = None
        
        return ConnectionContext(self)
