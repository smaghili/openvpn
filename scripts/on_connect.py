#!/usr/bin/env python3
"""
OpenVPN connection script with quota checking.
Uses environment variables for all paths.
"""
import os
import sys
import sqlite3
from datetime import datetime

def load_env_vars():
    """Load environment variables from environment.env file."""
    env_file = os.path.join(os.path.dirname(__file__), '..', 'environment.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_log_file():
    return os.environ.get('OPENVPN_LOG_FILE', '/var/log/openvpn/traffic_monitor.log')

def get_database_file():
    return os.environ.get('DATABASE_FILE', '/root/openvpn/openvpn_data/vpn_manager.db')

def check_user_quota():
    """
    Checks if a connecting user has exceeded their data quota.
    Called by OpenVPN's client-connect hook.
    Username is in the 'common_name' environment variable.
    Exits with code 1 (failure) if quota is exceeded, 0 (success) otherwise.
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
    timestamp = datetime.now().isoformat()

    if not username:
        sys.exit(0)

    try:
        # Direct database connection to avoid circular imports
        db_file = get_database_file()
        
        if not os.path.exists(db_file):
            # If database doesn't exist, allow connection
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: User '{username}' connected (no database found)\n")
            sys.exit(0)
        
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        
        if not user_row:
            # User not in database, allow connection
            conn.close()
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - INFO: User '{username}' connected (not in database)\n")
            sys.exit(0)
        
        user_id = user_row['id']
        
        # Check quota
        cursor.execute("SELECT quota_bytes, bytes_used FROM user_quotas WHERE user_id = ?", (user_id,))
        quota_row = cursor.fetchone()
        
        if quota_row:
            quota_bytes = quota_row['quota_bytes']
            bytes_used = quota_row['bytes_used']
            
            # A quota of 0 means unlimited traffic
            if quota_bytes > 0 and bytes_used >= quota_bytes:
                conn.close()
                with open(log_file, "a") as f:
                    f.write(f"{timestamp} - REJECT: User '{username}' quota exceeded ({bytes_used}/{quota_bytes} bytes)\n")
                sys.exit(1)
        
        conn.close()
        with open(log_file, "a") as f:
            f.write(f"{timestamp} - INFO: User '{username}' connected (quota OK)\n")
        sys.exit(0)

    except Exception as e:
        # In case of any script error, log it and allow the connection
        try:
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - ERROR in on_connect for user '{username}': {e}\n")
        except:
            pass
        sys.exit(0)

if __name__ == "__main__":
    check_user_quota()
