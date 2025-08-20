from .models import UserProtocol

class ProtocolRepository:
    def __init__(self, db):
        self.db = db

    def add_protocol(self, user_id, protocol, auth_type, cert_pem=None, key_pem=None):
        self.db.execute(
            "INSERT INTO user_protocols (user_id, protocol, auth_type, cert_pem, key_pem) VALUES (?, ?, ?, ?, ?)",
            (user_id, protocol, auth_type, cert_pem, key_pem)
        )

    def get_protocols_by_user(self, user_id):
        rows = self.db.query("SELECT * FROM user_protocols WHERE user_id = ?", (user_id,))
        return [UserProtocol(**row) for row in rows]

    def delete_protocols_by_user(self, user_id):
        self.db.execute("DELETE FROM user_protocols WHERE user_id = ?", (user_id,))