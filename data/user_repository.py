from .models import User

class UserRepository:
    def __init__(self, db):
        self.db = db

    def add_user(self, username, password_hash):
        self.db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )

    def get_user_by_username(self, username):
        row = self.db.query("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return User(**row)
        return None

    def get_user_by_id(self, user_id):
        row = self.db.query("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return User(**row)
        return None

    def delete_user(self, user_id):
        self.db.execute("DELETE FROM users WHERE id = ?", (user_id,))