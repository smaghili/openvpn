#!/usr/bin/env python3
import socket
import time
import os
import sys
import datetime

# Add project root to path (will be set properly below)
temp_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if temp_project_root not in sys.path:
    sys.path.insert(0, temp_project_root)

from config.env_loader import get_config_value, get_int_config
from data.db import Database
from data.user_repository import UserRepository

# --- Configuration ---
MANAGEMENT_HOST = get_config_value("OPENVPN_MANAGEMENT_HOST", "127.0.0.1")
MANAGEMENT_PORT = get_int_config("OPENVPN_MANAGEMENT_PORT", 7505)
CHECK_INTERVAL = get_int_config("MONITOR_INTERVAL", 45)

# Ensure interval is within safe bounds
if CHECK_INTERVAL < 30:
    CHECK_INTERVAL = 30
elif CHECK_INTERVAL > 60:
    CHECK_INTERVAL = 60
    
LOG_FILE = get_config_value("OPENVPN_LOG_FILE", "/var/log/openvpn/traffic_monitor.log")
MAX_LOG_SIZE = get_int_config("MAX_LOG_SIZE", 10485760)  # 10MB default

# Use VPNPaths for consistent path management
from config.paths import VPNPaths
PROJECT_ROOT = VPNPaths.get_project_root()

class OpenVPNMonitor:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.db = Database()
        self.user_repo = UserRepository(self.db)
        log_dir = os.path.dirname(LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)

    def _log(self, message):
        timestamp = datetime.datetime.now().isoformat()
        self._rotate_log_if_needed()
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} - MONITOR - {message}\n")
        except Exception as e:
            # Fallback to stderr if log file is not writable
            print(f"{timestamp} - MONITOR - {message}", file=sys.stderr)
            print(f"{timestamp} - LOG ERROR - {e}", file=sys.stderr)
    
    def _rotate_log_if_needed(self):
        try:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
                # Rotate log file
                backup_file = f"{LOG_FILE}.old"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(LOG_FILE, backup_file)
        except Exception:
            pass  # Ignore rotation errors

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Read the initial welcome message from the server
            self.sock.recv(1024) 
            self._log("Successfully connected to OpenVPN management interface.")
            return True
        except Exception as e:
            self._log(f"ERROR: Could not connect to management interface: {e}")
            return False

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _send_command(self, command, timeout=10):
        if not self.sock:
            self._log("ERROR: Not connected to management interface.")
            return None
        try:
            # Set socket timeout
            self.sock.settimeout(timeout)
            self.sock.sendall(f"{command}\n".encode())
            
            response = ""
            start_time = time.time()
            max_iterations = 100  # Prevent infinite loops
            iterations = 0
            
            while "END" not in response and (time.time() - start_time) < timeout and iterations < max_iterations:
                try:
                    data = self.sock.recv(4096).decode()
                    if not data:  # Connection closed
                        break
                    response += data
                    iterations += 1
                except socket.timeout:
                    self._log(f"Timeout waiting for response to command '{command}'")
                    break
                except socket.error as e:
                    self._log(f"Socket error while receiving response: {e}")
                    break
            
            # Reset socket to blocking mode
            self.sock.settimeout(None)
            return response if response else None
            
        except socket.error as e:
            self._log(f"ERROR: Socket error while sending command '{command}': {e}")
            self.disconnect()
            return None
        except Exception as e:
            self._log(f"ERROR: Unexpected error with command '{command}': {e}")
            self.disconnect()
            return None

    def get_status(self):
        return self._send_command("status")

    def kill_user(self, username):
        self._log(f"Attempting to disconnect user '{username}' due to quota exceeded.")
        response = self._send_command(f"kill {username}")
        if response and "SUCCESS" in response:
            self._log(f"Successfully disconnected user '{username}'.")
        else:
            self._log(f"Failed to disconnect user '{username}'. Response: {response}")

    def _parse_client_status(self, status_output):
        """Robust parsing of OpenVPN status output"""
        connected_users = {}
        
        if not status_output:
            return connected_users
            
        try:
            # Look for CLIENT LIST section
            if "CLIENT LIST" not in status_output:
                self._log("No CLIENT LIST section found in status output")
                return connected_users
            
            sections = status_output.split("CLIENT LIST")
            if len(sections) < 2:
                return connected_users
                
            # Get the client section
            client_data = sections[1]
            
            # Find the end of client list (usually ROUTING TABLE or GLOBAL STATS)
            end_markers = ["ROUTING TABLE", "GLOBAL STATS", "END"]
            for marker in end_markers:
                if marker in client_data:
                    client_data = client_data.split(marker)[0]
                    break
            
            # Parse each line
            lines = [line.strip() for line in client_data.strip().split('\n') if line.strip()]
            
            # Skip header line if it exists
            if lines and ('Common Name' in lines[0] or 'Real Address' in lines[0]):
                lines = lines[1:]
            
            for line in lines:
                if not line or line.startswith('#'):
                    continue
                    
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    try:
                        username = parts[0].strip()
                        if not username or username == 'UNDEF':
                            continue
                            
                        bytes_received = int(parts[2])
                        bytes_sent = int(parts[3])
                        
                        connected_users[username] = {
                            'bytes_received': bytes_received, 
                            'bytes_sent': bytes_sent
                        }
                        
                    except (ValueError, IndexError) as e:
                        self._log(f"Error parsing line '{line}': {e}")
                        continue
                        
        except Exception as e:
            self._log(f"Error parsing status output: {e}")
            
        return connected_users

    def check_quotas(self):
        status_output = self.get_status()
        if not status_output:
            self._log("Could not get status from OpenVPN. Skipping check.")
            return

        # Parse the status output with robust parsing
        connected_users = self._parse_client_status(status_output)
        
        if not connected_users:
            self._log("No connected users found or failed to parse status")
            return

        try:
            # Get all users from database with proper error handling
            all_users = self.user_repo.get_all_users_with_details()
            if not all_users:
                self._log("No users found in database")
                return
                
            user_quotas = {}
            for u in all_users:
                if u and u.get('username'):
                    user_quotas[u['username']] = {
                        'id': u.get('id'),
                        'quota': u.get('quota_bytes', 0),
                        'used': u.get('bytes_used', 0)
                    }

            # Check each connected user against quotas
            for username, traffic in connected_users.items():
                if username not in user_quotas:
                    continue

                quota_info = user_quotas[username]
                quota_bytes = quota_info.get('quota', 0)
                
                if quota_bytes == 0:  # Unlimited
                    continue

                # Calculate total usage
                historical_usage = quota_info.get('used', 0)
                current_session_usage = traffic['bytes_received'] + traffic['bytes_sent']
                total_usage = historical_usage + current_session_usage

                if total_usage > quota_bytes:
                    self._log(f"User '{username}' exceeded quota: {total_usage}/{quota_bytes} bytes")
                    self.kill_user(username)
                    
        except Exception as e:
            self._log(f"Error during quota check: {e}")


    def run_forever(self):
        self._log(f"Monitor service started. Check interval: {CHECK_INTERVAL} seconds")
        consecutive_failures = 0
        max_failures = 5
        
        while True:
            try:
                if not self.sock:
                    # If not connected, try to connect
                    if not self.connect():
                        consecutive_failures += 1
                        # Exponential backoff for connection failures
                        backoff_time = min(CHECK_INTERVAL * (2 ** min(consecutive_failures, 4)), 300)
                        self._log(f"Connection failed {consecutive_failures} times. Waiting {backoff_time}s before retry.")
                        time.sleep(backoff_time)
                        continue
                    else:
                        # Reset failure counter on successful connection
                        consecutive_failures = 0
                
                # Perform quota check
                self.check_quotas()
                consecutive_failures = 0  # Reset on successful operation
                
            except KeyboardInterrupt:
                self._log("Monitor service stopped by user")
                break
            except Exception as e:
                consecutive_failures += 1
                self._log(f"Unexpected error in main loop: {e}")
                
                # If too many consecutive failures, increase wait time
                if consecutive_failures >= max_failures:
                    self._log(f"Too many consecutive failures ({consecutive_failures}). Entering recovery mode.")
                    time.sleep(CHECK_INTERVAL * 2)
                    consecutive_failures = 0  # Reset after recovery wait
            
            # Normal interval wait
            time.sleep(CHECK_INTERVAL)
        
        # Cleanup on exit
        self.disconnect()
        self._log("Monitor service stopped.")

if __name__ == "__main__":
    monitor = OpenVPNMonitor(MANAGEMENT_HOST, MANAGEMENT_PORT)
    monitor.run_forever()
