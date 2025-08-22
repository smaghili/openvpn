import os
import queue
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import DatabaseError
from core.types import DatabaseResult

# Use VPNPaths for consistent path management
from config.paths import VPNPaths

DATABASE_DIR = VPNPaths.get_database_dir()
DATABASE_FILE = VPNPaths.get_database_file()

class Database:
    """Handles all low-level interactions with the SQLite database."""

    # Connection pools per database file
    _pools: Dict[str, queue.Queue] = {}
    _locks: Dict[str, threading.Lock] = {}

    def __init__(self, db_file: str = DATABASE_FILE) -> None:
        """Initialize the database connection and pool."""

        self.db_file = db_file
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

        # Ensure a pool exists for this database file
        if db_file not in Database._locks:
            Database._locks[db_file] = threading.Lock()
        self._ensure_pool()

    # Internal helpers -------------------------------------------------

    def _ensure_pool(self) -> None:
        """Create a connection pool for the database file if needed."""
        if self.db_file in Database._pools:
            return
        with Database._locks[self.db_file]:
            if self.db_file in Database._pools:
                return
            pool = queue.Queue(maxsize=self._calculate_pool_size())
            for _ in range(pool.maxsize):
                conn = sqlite3.connect(self.db_file, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                pool.put(conn)
            Database._pools[self.db_file] = pool

    def _get_from_pool(self) -> sqlite3.Connection:
        self._ensure_pool()
        return Database._pools[self.db_file].get()

    def _return_to_pool(self, conn: sqlite3.Connection) -> None:
        self._ensure_pool()
        Database._pools[self.db_file].put(conn)

    def _calculate_pool_size(self) -> int:
        """Determine an appropriate connection pool size."""
        cores = os.cpu_count() or 1
        # Provide multiple connections per core but avoid excessive handles
        return max(5, min(100, cores * 5))

    def connect(self) -> None:
        """Retrieve a connection from the pool."""
        if not self.conn:
            try:
                self.conn = self._get_from_pool()
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to retrieve database connection: {e}")

    def disconnect(self) -> None:
        """Return the connection to the pool."""
        if self.conn:
            self._return_to_pool(self.conn)
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
                    if exc_type:
                        self.conn.rollback()
                    else:
                        self.conn.commit()
                    self.db._return_to_pool(self.conn)
                    self.conn = None
                self.db.conn = None

        return ConnectionContext(self)
