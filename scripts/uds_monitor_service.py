#!/usr/bin/env python3
"""
OpenVPN Traffic Monitor Service - UDS Implementation
Connects to OpenVPN management interface via Unix Domain Socket for near-realtime traffic monitoring.
"""

import socket
import time
import os
import sys
import datetime
import threading
import sqlite3
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

# Add project root to path
temp_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if temp_project_root not in sys.path:
    sys.path.insert(0, temp_project_root)

from config.env_loader import get_config_value, get_int_config
from config.paths import VPNPaths
from data.db import Database
from data.user_repository import UserRepository

# Configuration
UDS_SOCKET_PATH = get_config_value("OPENVPN_UDS_SOCKET", "/run/openvpn-server/ovpn-mgmt-cert.sock")
BYTECOUNT_INTERVAL = get_int_config("BYTECOUNT_INTERVAL", 5)  # seconds
RECONCILE_INTERVAL = get_int_config("RECONCILE_INTERVAL", 300)  # 5 minutes
DB_FLUSH_INTERVAL = get_int_config("DB_FLUSH_INTERVAL", 30)  # seconds
QUOTA_BUFFER_BYTES = get_int_config("QUOTA_BUFFER_BYTES", 20 * 1024 * 1024)  # 20MB default
LOG_FILE = VPNPaths.get_log_file()
MAX_LOG_SIZE = get_int_config("MAX_LOG_SIZE", 10485760)  # 10MB

@dataclass
class SessionData:
    """Represents a single VPN session with traffic counters."""
    common_name: str
    client_id: str
    bytes_sent: int = 0
    bytes_received: int = 0
    last_bytes_sent: int = 0
    last_bytes_received: int = 0
    connected_at: datetime.datetime = None
    last_seen: datetime.datetime = None

class UDSOpenVPNMonitor:
    """UDS-based OpenVPN traffic monitor with near-realtime bytecount events."""
    
    def __init__(self):
        self.socket_path = UDS_SOCKET_PATH
        self.sock = None
        self.file_handle = None
        self.db = Database()
        self.user_repo = UserRepository(self.db)
        self.sessions: Dict[Tuple[str, str], SessionData] = {}
        self.user_totals: Dict[str, int] = {}
        self.last_reconcile = time.time()
        self.last_db_flush = time.time()
        self.running = False
        self.lock = threading.Lock()
        
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize database with WAL mode and optimizations
        self._init_database()
    
    def _init_database(self):
        """Initialize database with WAL mode and performance optimizations."""
        try:
            with self.db.get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=3000")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                
                # Ensure indexes exist
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_quotas_username 
                    ON user_quotas(user_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_traffic_logs_user_time 
                    ON traffic_logs(user_id, log_timestamp)
                """)
                
            self._log("Database initialized with WAL mode and optimizations")
        except Exception as e:
            self._log(f"ERROR: Database initialization failed: {e}")
            raise
    
    def _log(self, message: str):
        """Log message with timestamp and rotation."""
        timestamp = datetime.datetime.now().isoformat()
        self._rotate_log_if_needed()
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} - UDS_MONITOR - {message}\n")
        except Exception as e:
            print(f"{timestamp} - UDS_MONITOR - {message}", file=sys.stderr)
            print(f"{timestamp} - LOG ERROR - {e}", file=sys.stderr)
    
    def _rotate_log_if_needed(self):
        """Rotate log file if it exceeds maximum size."""
        try:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
                backup_file = f"{LOG_FILE}.old"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(LOG_FILE, backup_file)
        except Exception:
            pass
    
    def connect(self) -> bool:
        """Connect to OpenVPN management interface via UDS."""
        try:
            if not os.path.exists(self.socket_path):
                self._log(f"ERROR: UDS socket not found: {self.socket_path}")
                return False
            
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.file_handle = self.sock.makefile('rwb', buffering=0)
            
            # Read welcome message
            welcome = self.file_handle.readline().decode('utf-8', errors='ignore').strip()
            self._log(f"Connected to OpenVPN management interface: {welcome}")
            
            # Enable bytecount events for near-realtime monitoring
            self.file_handle.write(f"bytecount {BYTECOUNT_INTERVAL}\n".encode())
            self.file_handle.flush()
            
            # Enable state events for session tracking
            self.file_handle.write(b"state on\n")
            self.file_handle.flush()
            
            self._log(f"Enabled bytecount events every {BYTECOUNT_INTERVAL} seconds")
            return True
            
        except Exception as e:
            self._log(f"ERROR: Failed to connect to UDS socket: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from OpenVPN management interface."""
        try:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            if self.sock:
                self.sock.close()
                self.sock = None
            self._log("Disconnected from OpenVPN management interface")
        except Exception as e:
            self._log(f"ERROR: Error during disconnect: {e}")
    
    def _send_command(self, command: str) -> Optional[str]:
        """Send command to OpenVPN management interface."""
        try:
            if not self.file_handle:
                return None
            
            self.file_handle.write(f"{command}\n".encode())
            self.file_handle.flush()
            
            # Read response
            response_lines = []
            while True:
                line = self.file_handle.readline().decode('utf-8', errors='ignore').strip()
                if line == "END":
                    break
                if line == "SUCCESS:" or line == "ERROR:":
                    break
                response_lines.append(line)
            
            return "\n".join(response_lines)
            
        except Exception as e:
            self._log(f"ERROR: Command '{command}' failed: {e}")
            return None
    
    def _parse_bytecount_event(self, line: str):
        """Parse bytecount event from OpenVPN management interface."""
        try:
            # Format: >BYTECOUNT:<client_id>,<bytes_sent>,<bytes_received>
            if not line.startswith(">BYTECOUNT:"):
                return
            
            parts = line[11:].split(',')
            if len(parts) != 3:
                return
            
            client_id = parts[0]
            bytes_sent = int(parts[1])
            bytes_received = int(parts[2])
            
            # Get common name for this client_id
            common_name = self._get_common_name_for_client(client_id)
            if not common_name:
                return
            
            session_key = (common_name, client_id)
            now = datetime.datetime.now()
            
            with self.lock:
                if session_key not in self.sessions:
                    self.sessions[session_key] = SessionData(
                        common_name=common_name,
                        client_id=client_id,
                        connected_at=now,
                        last_seen=now
                    )
                
                session = self.sessions[session_key]
                session.last_seen = now
                
                # Calculate incremental traffic (clamp to prevent negative values)
                sent_increment = max(0, bytes_sent - session.last_bytes_sent)
                received_increment = max(0, bytes_received - session.last_bytes_received)
                
                session.bytes_sent += sent_increment
                session.bytes_received += received_increment
                session.last_bytes_sent = bytes_sent
                session.last_bytes_received = bytes_received
                
                # Update user totals
                total_increment = sent_increment + received_increment
                if common_name not in self.user_totals:
                    self.user_totals[common_name] = 0
                self.user_totals[common_name] += total_increment
                
                self._log(f"Session {session_key}: +{total_increment} bytes (sent: {sent_increment}, received: {received_increment})")
                
        except Exception as e:
            self._log(f"ERROR: Failed to parse bytecount event '{line}': {e}")
    
    def _get_common_name_for_client(self, client_id: str) -> Optional[str]:
        """Get common name for a client ID from status output."""
        try:
            status_output = self._send_command("status 3")
            if not status_output:
                return None
            
            for line in status_output.split('\n'):
                if line.startswith("OpenVPN CLIENT LIST"):
                    continue
                if line.startswith("Common Name"):
                    continue
                if line.startswith("ROUTING TABLE"):
                    break
                
                parts = line.split(',')
                if len(parts) >= 4 and parts[0] == client_id:
                    return parts[1]  # Common name is second field
            
            return None
            
        except Exception as e:
            self._log(f"ERROR: Failed to get common name for client {client_id}: {e}")
            return None
    
    def _parse_state_event(self, line: str):
        """Parse state event for session tracking."""
        try:
            # Format: >STATE:<client_id>,<state>,<common_name>,<remote_ip>
            if not line.startswith(">STATE:"):
                return
            
            parts = line[7:].split(',')
            if len(parts) < 3:
                return
            
            client_id = parts[0]
            state = parts[1]
            common_name = parts[2]
            
            session_key = (common_name, client_id)
            now = datetime.datetime.now()
            
            with self.lock:
                if state == "CONNECTED":
                    if session_key not in self.sessions:
                        self.sessions[session_key] = SessionData(
                            common_name=common_name,
                            client_id=client_id,
                            connected_at=now,
                            last_seen=now
                        )
                        self._log(f"New session started: {session_key}")
                
                elif state == "DISCONNECTED":
                    if session_key in self.sessions:
                        session = self.sessions[session_key]
                        total_bytes = session.bytes_sent + session.bytes_received
                        self._log(f"Session ended: {session_key}, total bytes: {total_bytes}")
                        
                        # Record session traffic
                        self._record_session_traffic(session)
                        
                        # Remove from active sessions
                        del self.sessions[session_key]
                        
                        # Update user totals
                        if common_name in self.user_totals:
                            self.user_totals[common_name] -= total_bytes
                            if self.user_totals[common_name] <= 0:
                                del self.user_totals[common_name]
                
        except Exception as e:
            self._log(f"ERROR: Failed to parse state event '{line}': {e}")
    
    def _record_session_traffic(self, session: SessionData):
        """Record session traffic to database."""
        try:
            total_bytes = session.bytes_sent + session.bytes_received
            if total_bytes == 0:
                return
            
            # Get user ID from common name
            user = self.user_repo.get_user_by_username(session.common_name)
            if not user:
                self._log(f"WARNING: User not found for common name: {session.common_name}")
                return
            
            with self.db.get_connection() as conn:
                # Record session traffic
                conn.execute("""
                    INSERT INTO traffic_logs (user_id, bytes_sent, bytes_received, log_timestamp)
                    VALUES (?, ?, ?, ?)
                """, (user['id'], session.bytes_sent, session.bytes_received, session.connected_at))
                
                # Update user quota usage
                conn.execute("""
                    INSERT INTO user_quotas (user_id, bytes_used)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        bytes_used = user_quotas.bytes_used + excluded.bytes_used,
                        updated_at = CURRENT_TIMESTAMP
                """, (user['id'], total_bytes))
                
            self._log(f"Recorded session traffic for {session.common_name}: {total_bytes} bytes")
            
        except Exception as e:
            self._log(f"ERROR: Failed to record session traffic: {e}")
    
    def _reconcile_sessions(self):
        """Reconcile sessions with full status output."""
        try:
            status_output = self._send_command("status 3")
            if not status_output:
                return
            
            current_sessions = set()
            now = datetime.datetime.now()
            
            # Parse CLIENT_LIST section
            in_client_list = False
            for line in status_output.split('\n'):
                if line.startswith("OpenVPN CLIENT LIST"):
                    in_client_list = True
                    continue
                if line.startswith("ROUTING TABLE"):
                    break
                
                if in_client_list and line.strip() and not line.startswith("Common Name"):
                    parts = line.split(',')
                    if len(parts) >= 4:
                        client_id = parts[0]
                        common_name = parts[1]
                        session_key = (common_name, client_id)
                        current_sessions.add(session_key)
                        
                        # Update last seen for existing sessions
                        with self.lock:
                            if session_key in self.sessions:
                                self.sessions[session_key].last_seen = now
            
            # Clean up disconnected sessions
            with self.lock:
                disconnected_sessions = []
                for session_key in list(self.sessions.keys()):
                    if session_key not in current_sessions:
                        session = self.sessions[session_key]
                        # Check if session has been inactive for more than 30 seconds
                        if (now - session.last_seen).total_seconds() > 30:
                            disconnected_sessions.append(session)
                            del self.sessions[session_key]
                
                # Record traffic for disconnected sessions
                for session in disconnected_sessions:
                    self._record_session_traffic(session)
            
            self._log(f"Reconciled {len(current_sessions)} active sessions")
            
        except Exception as e:
            self._log(f"ERROR: Failed to reconcile sessions: {e}")
    
    def _check_quotas_and_enforce(self):
        """Check user quotas and disconnect violators."""
        try:
            with self.lock:
                for common_name, total_bytes in self.user_totals.items():
                    user = self.user_repo.get_user_by_username(common_name)
                    if not user:
                        continue
                    
                    # Get user quota
                    quota_data = self.user_repo.get_user_quota(user['id'])
                    if not quota_data or quota_data['quota_bytes'] == 0:
                        continue  # Unlimited quota
                    
                    quota_bytes = quota_data['quota_bytes']
                    current_usage = quota_data['bytes_used'] + total_bytes
                    
                    if current_usage >= quota_bytes + QUOTA_BUFFER_BYTES:
                        self._log(f"QUOTA EXCEEDED: {common_name} - {current_usage}/{quota_bytes} bytes")
                        self._disconnect_user(common_name, "quota_exceeded")
            
        except Exception as e:
            self._log(f"ERROR: Failed to check quotas: {e}")
    
    def _disconnect_user(self, common_name: str, reason: str):
        """Disconnect user from all sessions."""
        try:
            sessions_to_disconnect = []
            with self.lock:
                for session_key, session in self.sessions.items():
                    if session.common_name == common_name:
                        sessions_to_disconnect.append(session_key)
            
            for session_key in sessions_to_disconnect:
                client_id = session_key[1]
                self._send_command(f"kill {client_id}")
                self._log(f"Disconnected user {common_name} (client {client_id}): {reason}")
                
                # Record the session traffic before removing
                with self.lock:
                    if session_key in self.sessions:
                        session = self.sessions[session_key]
                        self._record_session_traffic(session)
                        del self.sessions[session_key]
            
        except Exception as e:
            self._log(f"ERROR: Failed to disconnect user {common_name}: {e}")
    
    def _flush_database(self):
        """Flush any pending database operations."""
        try:
            # This is handled by SQLite WAL mode, but we can force a checkpoint
            with self.db.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._log("Database checkpoint completed")
        except Exception as e:
            self._log(f"ERROR: Database flush failed: {e}")
    
    def _read_events(self):
        """Read events from OpenVPN management interface."""
        try:
            while self.running and self.file_handle:
                line = self.file_handle.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore').strip()
                if not line_str:
                    continue
                
                # Parse different event types
                if line_str.startswith(">BYTECOUNT:"):
                    self._parse_bytecount_event(line_str)
                elif line_str.startswith(">STATE:"):
                    self._parse_state_event(line_str)
                elif line_str.startswith(">INFO:"):
                    # Log info messages
                    self._log(f"INFO: {line_str[6:]}")
                elif line_str.startswith(">HOLD:"):
                    # Handle hold events
                    self._log(f"HOLD: {line_str[6:]}")
                elif line_str.startswith(">LOG:"):
                    # Log OpenVPN log messages
                    self._log(f"OPENVPN: {line_str[5:]}")
                
        except Exception as e:
            self._log(f"ERROR: Event reading failed: {e}")
    
    def run_forever(self):
        """Main monitoring loop."""
        self.running = True
        self._log("Starting UDS-based OpenVPN traffic monitor")
        
        while self.running:
            try:
                # Connect to management interface
                if not self.connect():
                    self._log("Failed to connect, retrying in 30 seconds...")
                    time.sleep(30)
                    continue
                
                # Start event reading thread
                event_thread = threading.Thread(target=self._read_events, daemon=True)
                event_thread.start()
                
                # Main monitoring loop
                while self.running:
                    current_time = time.time()
                    
                    # Periodic quota checking
                    self._check_quotas_and_enforce()
                    
                    # Periodic reconciliation
                    if current_time - self.last_reconcile >= RECONCILE_INTERVAL:
                        self._reconcile_sessions()
                        self.last_reconcile = current_time
                    
                    # Periodic database flush
                    if current_time - self.last_db_flush >= DB_FLUSH_INTERVAL:
                        self._flush_database()
                        self.last_db_flush = current_time
                    
                    time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                self._log("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self._log(f"ERROR: Monitoring loop failed: {e}")
                time.sleep(30)  # Wait before retrying
            finally:
                self.disconnect()
        
        self.running = False
        self._log("UDS-based OpenVPN traffic monitor stopped")

def main():
    """Main entry point."""
    monitor = UDSOpenVPNMonitor()
    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        monitor._log("Shutdown requested")
    finally:
        monitor.disconnect()

if __name__ == "__main__":
    main() 