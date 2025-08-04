import bcrypt
from data.user_repository import UserRepository
from data.protocol_repository import ProtocolRepository
from core.openvpn_manager import OpenVPNManager
from core.login_user_manager import LoginUserManager

class UserService:
    """
    Handles high-level user business logic, such as creation, removal, and listing.
    Acts as a facade, coordinating between the data layer and the core managers.
    """
    def __init__(
        self,
        user_repo: UserRepository,
        protocol_repo: ProtocolRepository,
        openvpn_mgr: OpenVPNManager,
        login_user_mgr: LoginUserManager
    ):
        self.user_repo = user_repo
        self.protocol_repo = protocol_repo
        self.openvpn_mgr = openvpn_mgr
        self.login_user_mgr = login_user_mgr

    def create_user(self, username, password):
        """
        Creates a new user with both certificate and login authentication.
        1. Checks for existing user.
        2. Creates a record in the database.
        3. Creates a system user for PAM authentication.
        4. Creates an OpenVPN certificate and .ovpn file.
        """
        if self.user_repo.get_user_by_username(username):
            raise ValueError(f"User '{username}' already exists.")

        password_hash = self._hash_password(password)
        self.user_repo.add_user(username, password_hash)
        user = self.user_repo.get_user_by_username(username)

        # Delegate to the respective managers
        self.login_user_mgr.add_user(username, password)
        self.openvpn_mgr.add_user(user)

        # Record protocol usage in the database
        self.protocol_repo.add_protocol(user_id=user.id, protocol='openvpn', auth_type='certificate')
        self.protocol_repo.add_protocol(user_id=user.id, protocol='openvpn', auth_type='login')
        
        return user

    def remove_user(self, username):
        """
        Removes a user completely from the system.
        1. Revokes OpenVPN certificate.
        2. Deletes the system user.
        3. Deletes all database records.
        """
        user = self.user_repo.get_user_by_username(username)
        if not user:
            raise ValueError(f"User '{username}' not found.")

        # Delegate removal to managers
        self.openvpn_mgr.remove_user(user)
        self.login_user_mgr.remove_user(username)

        # Clean up database records
        self.protocol_repo.delete_protocols_by_user(user.id)
        self.user_repo.delete_user(user.id)

    def list_users(self):
        """Returns a list of all registered users."""
        users = []
        for row in self.user_repo.list_all_users():
            users.append({"username": row["username"], "status": row["status"]})
        return users
        
    def _hash_password(self, password):
        """Hashes a password for secure storage."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
