import sqlite3

class Database:
    def __init__(self, db_path='vpn_manager.db'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def execute(self, query, params=()):
        with self.conn:
            return self.conn.execute(query, params)

    def query(self, query, params=()):
        return self.conn.execute(query, params)

    def close(self):
        self.conn.close()