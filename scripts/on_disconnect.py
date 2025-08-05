#!/usr/bin/env python3
import os
import sys
import datetime

# Add project root to path for module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment configuration first
from config.env_loader import get_config_value

from data.db import Database

def update_traffic_usage():
    """
    Updates the total data usage for a disconnected user and logs the session.
    Called by OpenVPN's client-disconnect hook.
    
    Environment variables from OpenVPN:
    - common_name: The username.
    - bytes_sent: Bytes sent during the session.
    - bytes_received: Bytes received during the session.
    """
    log_file = get_config_value("OPENVPN_LOG_FILE", "/var/log/openvpn/traffic_monitor.log")
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    username = os.environ.get("common_name")
    bytes_sent = int(os.environ.get("bytes_sent", 0))
    bytes_received = int(os.environ.get("bytes_received", 0))

    if not username:
        sys.exit(0)

    total_session_bytes = bytes_sent + bytes_received
    if total_session_bytes == 0:
        sys.exit(0)

    try:
        db = Database()
        
        # Get user_id from username
        user_result = db.execute_query("SELECT id FROM users WHERE username = ?", (username,))
        if not user_result:
            sys.exit(0)
        user_id = user_result[0]['id']

        # Use transaction to ensure atomicity
        db.execute_query("BEGIN TRANSACTION")
        
        try:
            # 1. Update the cumulative usage in the user_quotas table
            update_query = "UPDATE user_quotas SET bytes_used = bytes_used + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
            db.execute_query(update_query, (total_session_bytes, user_id))

            # 2. Log the session details into traffic_logs for historical analysis
            log_query = "INSERT INTO traffic_logs (user_id, bytes_sent, bytes_received, log_timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
            db.execute_query(log_query, (user_id, bytes_sent, bytes_received))
            
            # Commit the transaction
            db.execute_query("COMMIT")
            
            # Log successful update
            timestamp = datetime.datetime.now().isoformat()
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: Updated usage for user '{username}': +{total_session_bytes} bytes\n")
                
        except Exception as e:
            # Rollback on any error
            db.execute_query("ROLLBACK")
            raise e

    except Exception as e:
        timestamp = datetime.datetime.now().isoformat()
        with open(log_file, "a") as f:
            f.write(f"{timestamp} - ERROR in on_disconnect for user '{username}': {e}\n")
    
    sys.exit(0)

if __name__ == "__main__":
    update_traffic_usage()
