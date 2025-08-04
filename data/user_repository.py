from .db import Database

class UserRepository:
    """
    Handles all data access logic related to users.
    It abstracts the database interactions from the rest of the application.
    """
    def __init__(self, db: Database):
        """
        Initializes the repository with a database connection object.

        Args:
            db (Database): An instance of the Database class.
        """
        self.db = db
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        """
        Ensures the 'users' table exists in the database.
        This is a safe operation that will only create the table if it's missing.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            config_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute_query(create_table_query)

    def add_user(self, username: str, auth_type: str, config_data: str = None):
        """
        Adds a new user record to the database.

        Args:
            username (str): The name of the user.
            auth_type (str): The authentication type (e.g., 'certificate', 'login').
            config_data (str, optional): The user's .ovpn config file content.
        """
        query = "INSERT INTO users (username, auth_type, config_data) VALUES (?, ?, ?)"
        self.db.execute_query(query, (username, auth_type, config_data))

    def get_user_by_username(self, username: str, auth_type: str = None):
        """
        Retrieves a user's record(s) from the database by their username.
        If auth_type is specified, it filters for that specific type.

        Args:
            username (str): The name of the user.
            auth_type (str, optional): The specific auth type to find.

        Returns:
            dict or list: A single user dict if auth_type is specified and found,
                          a list of user dicts if auth_type is not specified,
                          or None if no user is found.
        """
        if auth_type:
            query = "SELECT * FROM users WHERE username = ? AND auth_type = ?"
            params = (username, auth_type)
            result = self.db.execute_query(query, params)
            return result[0] if result else None
        else:
            query = "SELECT * FROM users WHERE username = ?"
            params = (username,)
            return self.db.execute_query(query, params)

    def get_all_users(self) -> list:
        """
        Retrieves all user records from the database.

        Returns:
            list: A list of dictionaries, where each dictionary represents a user.
        """
        query = "SELECT * FROM users ORDER BY username"
        return self.db.execute_query(query)

    def remove_user(self, username: str):
        """
        Removes all records associated with a given username from the database.

        Args:
            username (str): The name of the user to remove.
        """
        query = "DELETE FROM users WHERE username = ?"
        self.db.execute_query(query, (username,))
