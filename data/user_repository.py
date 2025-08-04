from .db import Database
import hashlib

class UserRepository:
    def __init__(self, db: Database):
        self.db = db
        self._create_tables_if_not_exist()

    def _create_tables_if_not_exist(self):
        import os
        schema_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.sql')
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema = f.read()
            self.db.execute_script(schema)

    def add_user(self, username: str, password_hash: str = None):
        query = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        self.db.execute_query(query, (username, password_hash))
        
        user_result = self.db.execute_query("SELECT id FROM users WHERE username = ?", (username,))
        return user_result[0]['id'] if user_result else None

    def add_user_protocol(self, user_id: int, protocol: str, auth_type: str, cert_pem: str = None, key_pem: str = None):
        query = """
        INSERT INTO user_protocols (user_id, protocol, auth_type, cert_pem, key_pem) 
        VALUES (?, ?, ?, ?, ?)
        """
        self.db.execute_query(query, (user_id, protocol, auth_type, cert_pem, key_pem))

    def get_user_by_username(self, username: str, auth_type: str = None):
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
            return self.db.execute_query(query, params)

    def get_all_users(self) -> list:
        query = """
        SELECT u.username, u.status, u.created_at, up.auth_type, up.protocol
        FROM users u
        LEFT JOIN user_protocols up ON u.id = up.user_id
        ORDER BY u.username, up.auth_type
        """
        return self.db.execute_query(query)

    def remove_user(self, username: str):
        query = "DELETE FROM users WHERE username = ?"
        self.db.execute_query(query, (username,))

    def get_user_certificate_config(self, username: str):
        user_data = self.get_user_by_username(username, 'certificate')
        if not user_data or not user_data.get('cert_pem'):
            return None
        from core.openvpn_manager import OpenVPNManager
        from config.shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
        
        openvpn_manager = OpenVPNManager()
        ca_cert = openvpn_manager._read_file(f"{openvpn_manager.OPENVPN_DIR}/ca.crt")
        tls_crypt_key = openvpn_manager._read_file(f"{openvpn_manager.OPENVPN_DIR}/tls-crypt.key")
        
        user_specific_certs = USER_CERTS_TEMPLATE.format(
            user_cert=user_data['cert_pem'],
            user_key=user_data['key_pem']
        )
        
        return CLIENT_TEMPLATE.format(
            proto=openvpn_manager.settings.get("cert_proto", "udp"),
            server_ip=openvpn_manager.settings.get("public_ip"),
            port=openvpn_manager.settings.get("cert_port", "1194"),
            ca_cert=ca_cert,
            user_specific_certs=user_specific_certs,
            tls_crypt_key=tls_crypt_key
        )
