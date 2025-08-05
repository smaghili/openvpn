#!/usr/bin/env python3
import os
import sys

# This is crucial for the script to find other modules in the project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment configuration first
from config.env_loader import get_config_value

# It's better to import after setting the path
from data.db import Database
from data.user_repository import UserRepository

def check_user_quota():
    """
    Checks if a connecting user has exceeded their data quota.
    Called by OpenVPN's client-connect hook.
    Username is in the 'common_name' environment variable.
    Exits with code 1 (failure) if quota is exceeded, 0 (success) otherwise.
    """
    log_file = get_config_value("OPENVPN_LOG_FILE", "/var/log/openvpn/traffic_monitor.log")
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    username = os.environ.get("common_name")

    if not username:
        # Allow connection if no username is passed, but this is unusual.
        sys.exit(0)

    try:
        db = Database()
        user_repo = UserRepository(db)
        
        user = user_repo.find_user_by_username(username)
        if not user:
            # If user is not in our database, let OpenVPN decide.
            sys.exit(0)
            
        quota_status = user_repo.get_user_quota_status(user['id'])
        
        if quota_status:
            quota_bytes = quota_status.get('quota_bytes', 0)
            bytes_used = quota_status.get('bytes_used', 0)

            # A quota of 0 means unlimited traffic.
            if quota_bytes > 0 and bytes_used >= quota_bytes:
                with open(log_file, "a") as f:
                    f.write(f"INFO: User '{username}' connection rejected, quota exceeded.\n")
                # Exit with 1 to tell OpenVPN to reject the connection
                sys.exit(1)

    except Exception as e:
        # In case of any script error, log it and allow the connection
        # to prevent service disruption from script bugs.
        with open(log_file, "a") as f:
            f.write(f"ERROR in on_connect for user '{username}': {e}\n")
        sys.exit(0)

    # If all checks pass, exit with 0 to allow the connection.
    sys.exit(0)

if __name__ == "__main__":
    check_user_quota()
