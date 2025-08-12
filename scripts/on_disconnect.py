#!/usr/bin/env python3
"""
OpenVPN disconnection script with database logging.
Uses environment variables for all paths.
"""
import os
import sys
import sqlite3
from datetime import datetime
from config.paths import VPNPaths

def load_env_vars():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_log_file():
    return os.environ.get('OPENVPN_LOG_FILE', '/var/log/openvpn/traffic_monitor.log')

def update_traffic_usage():
    """
    Updates the total data usage for a disconnected user and logs the session.
    Called by OpenVPN's client-disconnect hook.
    
    Environment variables from OpenVPN:
    - common_name: The username.
    - bytes_sent: Bytes sent during the session.
    - bytes_received: Bytes received during the session.
    """
    # Load environment variables first
    load_env_vars()
    
    log_file = get_log_file()
    log_dir = os.path.dirname(log_file)
    
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass
    
    username = os.environ.get("common_name")
    bytes_sent = int(os.environ.get("bytes_sent", 0))
    bytes_received = int(os.environ.get("bytes_received", 0))
    timestamp = datetime.now().isoformat()

    if not username:
        sys.exit(0)

    total_session_bytes = bytes_sent + bytes_received
    if total_session_bytes == 0:
        try:
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: User '{username}' disconnected (no traffic)\n")
        except:
            pass
        sys.exit(0)

    try:
        # Direct database connection to avoid circular imports
        db_file = VPNPaths.get_database_file()
        
        if not os.path.exists(db_file):
            # If database doesn't exist, just log to file
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: User '{username}' disconnected. Sent: {bytes_sent}, Received: {bytes_received} (no database)\n")
            sys.exit(0)
        
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get user ID from username
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: User '{username}' disconnected. Sent: {bytes_sent}, Received: {bytes_received} (user not in database)\n")
            sys.exit(0)
        
        user_id = user_row['id']

        # Use transaction to ensure atomicity
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            # 1. Update the cumulative usage in the user_quotas table
            cursor.execute("UPDATE user_quotas SET bytes_used = bytes_used + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", 
                          (total_session_bytes, user_id))

            # 2. Log the session details into traffic_logs for historical analysis
            cursor.execute("INSERT INTO traffic_logs (user_id, bytes_sent, bytes_received, log_timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", 
                          (user_id, bytes_sent, bytes_received))
            
            # Commit the transaction
            cursor.execute("COMMIT")
            
            # Log successful update
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: Updated usage for user '{username}': +{total_session_bytes} bytes\n")
                
        except Exception as e:
            # Rollback on any error
            cursor.execute("ROLLBACK")
            raise e
        finally:
            conn.close()

    except Exception as e:
        # Log error but don't fail
        try:
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - ERROR in on_disconnect for user '{username}': {e}\n")
        except:
            pass
    
    sys.exit(0)

if __name__ == "__main__":
    update_traffic_usage()
