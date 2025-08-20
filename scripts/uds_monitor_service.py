#!/usr/bin/env python3
import socket
import time
import os
import sys
import datetime
import threading
import sqlite3
import queue
from typing import Dict, Tuple, Optional, Set
from dataclasses import dataclass

temp_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if temp_project_root not in sys.path:
    sys.path.insert(0, temp_project_root)

from config.env_loader import get_config_value, get_int_config
from config.paths import VPNPaths
from data.db import Database
from data.user_repository import UserRepository

UDS_SOCKET_PATH_CERT = get_config_value("OPENVPN_UDS_SOCKET", "/run/openvpn-server/ovpn-mgmt-cert.sock")
UDS_SOCKET_PATH_LOGIN = "/run/openvpn-server/ovpn-mgmt-login.sock"
FLUSH_INTERVAL = 0.5  # Flush every 0.5 seconds for real-time updates
LOG_FILE = VPNPaths.get_log_file()
MAX_LOG_SIZE = get_int_config("MAX_LOG_SIZE", 10485760)
MAX_SESSIONS = get_int_config("MAX_SESSIONS", 1000)
DATABASE_FILE = VPNPaths.get_database_file()

@dataclass
class SessionData:
    common_name: str
    client_id: str
    bytes_sent: int = 0
    bytes_received: int = 0
    last_bytes_sent: int = 0
    last_bytes_received: int = 0
    connected_at: datetime.datetime = None
    last_seen: datetime.datetime = None

class BackgroundDBWriter:
    def __init__(self, database_file: str):
        self.database_file = database_file
        self.write_queue = queue.Queue(maxsize=10000)
        self.backup_queue = []
        self.conn = None
        self.running = True
        self.max_retry_attempts = 3
        self.setup_database()
        self.writer_thread = threading.Thread(target=self.background_writer, daemon=True)
        self.writer_thread.start()

    def setup_database(self):
        self.conn = sqlite3.connect(self.database_file, check_same_thread=False)
        # Optimize SQLite for high-performance updates
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")  
        self.conn.execute("PRAGMA cache_size=50000")  # Increased cache
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
        self.conn.execute("PRAGMA optimize")

    def queue_updates(self, updates: Dict[str, Tuple[int, int]]):
        if updates:
            try:
                self.write_queue.put(updates.copy(), timeout=0.1)
            except queue.Full:
                self.backup_queue.extend(updates.items())
                if len(self.backup_queue) > 50000:
                    self.backup_queue = self.backup_queue[-25000:]

    def background_writer(self):
        while self.running:
            try:
                updates = self.write_queue.get(timeout=1.0)
                self.bulk_update_with_retry(updates)
            except queue.Empty:
                if self.backup_queue:
                    backup_updates = dict(self.backup_queue[:1000])
                    self.backup_queue = self.backup_queue[1000:]
                    self.bulk_update_with_retry(backup_updates)
                continue
            except Exception as e:
                self._log_error(f"Background writer error: {e}")
                time.sleep(5)

    def bulk_update_with_retry(self, updates: Dict[str, Tuple[int, int]]):
        for attempt in range(self.max_retry_attempts):
            try:
                self.bulk_update(updates)
                return
            except Exception as e:
                self._log_error(f"Bulk update attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retry_attempts - 1:
                    self.backup_queue.extend(updates.items())
                else:
                    time.sleep(2 ** attempt)

    def bulk_update(self, updates: Dict[str, Tuple[int, int]]):
        if not updates:
            return
            
        try:
            with self.conn:
                cursor = self.conn.cursor()
                
                # Prepare batch data for maximum efficiency
                quota_updates = []
                log_inserts = []
                
                for username, (bytes_sent, bytes_received) in updates.items():
                    total_bytes = bytes_sent + bytes_received
                    quota_updates.append((total_bytes, username))
                    
                    # Only log every 10th update to reduce database load
                    if len(log_inserts) < len(updates) // 10 and total_bytes > 10240:
                        log_inserts.append((bytes_sent, bytes_received, username))
                
                # Batch execute quota updates
                if quota_updates:
                    cursor.executemany("""
                        UPDATE user_quotas 
                        SET bytes_used = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = (SELECT id FROM users WHERE username = ?)
                    """, quota_updates)
                
                # Batch execute log inserts (reduced frequency)
                if log_inserts:
                    cursor.executemany("""
                        INSERT INTO traffic_logs (user_id, bytes_sent, bytes_received, log_timestamp)
                        SELECT id, ?, ?, CURRENT_TIMESTAMP FROM users WHERE username = ?
                    """, log_inserts)
                    
        except Exception as e:
            self._log_error(f"Bulk update failed: {e}")

    def _log_error(self, message: str):
        timestamp = datetime.datetime.now().isoformat()
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} - DB_WRITER_ERROR - {message}\n")
        except:
            pass

    def shutdown(self):
        self.running = False
        if self.conn:
            self.conn.close()

class OptimizedUDSMonitor:
    def __init__(self):
        self.socket_path_cert = UDS_SOCKET_PATH_CERT
        self.socket_path_login = UDS_SOCKET_PATH_LOGIN
        self.sock_cert = None
        self.sock_login = None
        self.file_handle_cert = None
        self.file_handle_login = None
        self.traffic_buffer: Dict[str, Tuple[int, int]] = {}
        self.dirty_users: Set[str] = set()
        self.sessions: Dict[Tuple[str, str], SessionData] = {}
        self.user_cache: Dict[str, int] = {}
        self.user_repo = UserRepository(Database())
        self.db_writer = BackgroundDBWriter(DATABASE_FILE)
        self.last_flush = time.time()
        self.last_status_update = time.time()
        self.running = False
        self.lock = threading.Lock()
        self.status_cache: Dict[str, str] = {}
        log_dir = os.path.dirname(LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)

    def _log(self, message: str):
        timestamp = datetime.datetime.now().isoformat()
        self._rotate_log_if_needed()
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"{timestamp} - OPTIMIZED_MONITOR - {message}\n")
        except Exception as e:
            print(f"{timestamp} - OPTIMIZED_MONITOR - {message}", file=sys.stderr)

    def _rotate_log_if_needed(self):
        try:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
                backup_file = f"{LOG_FILE}.old"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(LOG_FILE, backup_file)
        except:
            pass

    def connect(self) -> bool:
        connected = False
        try:
            # Connect to certificate server
            if os.path.exists(self.socket_path_cert):
                self.sock_cert = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock_cert.connect(self.socket_path_cert)
                self.file_handle_cert = self.sock_cert.makefile('rwb', buffering=0)
                welcome = self.file_handle_cert.readline().decode('utf-8', errors='ignore').strip()
                self._log(f"Connected to OpenVPN cert: {welcome}")
                # Close connection immediately after welcome
                self.file_handle_cert.close()
                self.sock_cert.close()
                self.file_handle_cert = None
                self.sock_cert = None
                connected = True
            else:
                self._log(f"WARNING: Cert socket not found: {self.socket_path_cert}")
            
            # Connect to login server
            if os.path.exists(self.socket_path_login):
                self.sock_login = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock_login.connect(self.socket_path_login)
                self.file_handle_login = self.sock_login.makefile('rwb', buffering=0)
                welcome = self.file_handle_login.readline().decode('utf-8', errors='ignore').strip()
                self._log(f"Connected to OpenVPN login: {welcome}")
                # Close connection immediately after welcome
                self.file_handle_login.close()
                self.sock_login.close()
                self.file_handle_login = None
                self.sock_login = None
                connected = True
            else:
                self._log(f"WARNING: Login socket not found: {self.socket_path_login}")
            
            return connected
        except Exception as e:
            self._log(f"ERROR: Connection failed: {e}")
            return False

    def disconnect(self):
        try:
            if self.file_handle_cert:
                self.file_handle_cert.close()
                self.file_handle_cert = None
            if self.sock_cert:
                self.sock_cert.close()
                self.sock_cert = None
            if self.file_handle_login:
                self.file_handle_login.close()
                self.file_handle_login = None
            if self.sock_login:
                self.sock_login.close()
                self.sock_login = None
        except Exception as e:
            self._log(f"ERROR: Disconnect error: {e}")

    def _parse_bytecount_event(self, line: str):
        try:
            if not line.startswith(">BYTECOUNT:"):
                return
            parts = line[11:].split(',')
            if len(parts) != 3:
                return
            client_id = parts[0]
            bytes_sent = int(parts[1])
            bytes_received = int(parts[2])
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
                sent_increment = max(0, bytes_sent - session.last_bytes_sent)
                received_increment = max(0, bytes_received - session.last_bytes_received)
                session.bytes_sent += sent_increment
                session.bytes_received += received_increment
                session.last_bytes_sent = bytes_sent
                session.last_bytes_received = bytes_received
                if sent_increment > 0 or received_increment > 0:
                    current_sent, current_received = self.traffic_buffer.get(common_name, (0, 0))
                    self.traffic_buffer[common_name] = (current_sent + sent_increment, current_received + received_increment)
                    self.dirty_users.add(common_name)
                    if time.time() - self.last_flush >= FLUSH_INTERVAL:
                        self.smart_flush()
        except Exception as e:
            self._log(f"ERROR: Parse bytecount failed: {e}")

    def _update_status_cache(self):
        try:
            # Always update (remove timing restriction for debugging)
            # Get status from cert server only (most users are here)
            status_output = self._send_command("status", "cert")
            if status_output:
                self._parse_status_output(status_output)
                self.last_status_update = time.time()
            else:
                self._log("No status output received")
        except Exception as e:
            self._log(f"ERROR: Status cache update failed: {e}")
            # Don't crash on error, just continue
    
    def _parse_status_output(self, status_output: str):
        for line in status_output.split('\n'):
            if line.startswith("OpenVPN CLIENT LIST"):
                continue
            if line.startswith("Common Name"):
                continue
            if line.startswith("ROUTING TABLE"):
                break
            parts = line.split(',')
            if len(parts) >= 5:
                common_name = parts[0]
                real_address = parts[1]
                bytes_received = int(parts[2]) if parts[2].isdigit() else 0
                bytes_sent = int(parts[3]) if parts[3].isdigit() else 0
                # No need for status_cache in polling mode
                
                # Update traffic data
                if common_name and (bytes_sent > 0 or bytes_received > 0):
                    self._update_traffic_data(common_name, bytes_sent, bytes_received)
    
    def _update_traffic_data(self, common_name: str, bytes_sent: int, bytes_received: int):
        try:
            with self.lock:
                # Always update with absolute values (not incremental)
                self.traffic_buffer[common_name] = (bytes_sent, bytes_received)
                self.dirty_users.add(common_name)
                
                # Log every update for debugging
                self._log(f"Traffic update for {common_name}: sent={bytes_sent}, received={bytes_received}")
        except Exception as e:
            self._log(f"ERROR: Traffic update failed: {e}")

    def _get_common_name_for_client(self, client_id: str) -> Optional[str]:
        self._update_status_cache()
        return self.status_cache.get(client_id)

    def _send_command(self, command: str, socket_type: str = "cert") -> Optional[str]:
        try:
            socket_path = self.socket_path_cert if socket_type == "cert" else self.socket_path_login
            if not os.path.exists(socket_path):
                return None
            
            # Create temporary connection
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            file_handle = sock.makefile('rwb', buffering=0)
            
            # Read welcome message
            welcome = file_handle.readline().decode('utf-8', errors='ignore').strip()
            
            # Send command
            file_handle.write(f"{command}\n".encode())
            file_handle.flush()
            
            response_lines = []
            while True:
                line = file_handle.readline().decode('utf-8', errors='ignore').strip()
                if line == "END" or line == "SUCCESS:" or line == "ERROR:":
                    break
                response_lines.append(line)
            
            # Close connection
            file_handle.close()
            sock.close()
            
            return "\n".join(response_lines)
        except Exception as e:
            self._log(f"ERROR: Command failed: {e}")
            return None

    def smart_flush(self):
        with self.lock:
            if not self.dirty_users:
                return
            updates = {}
            for user in self.dirty_users:
                if user in self.traffic_buffer:
                    updates[user] = self.traffic_buffer[user]
            if updates:
                self._log(f"Flushing updates for {len(updates)} users")
                self.db_writer.queue_updates(updates)
            self.dirty_users.clear()
            self.last_flush = time.time()

    def _check_quotas_and_enforce(self):
        try:
            with self.lock:
                for common_name in list(self.traffic_buffer.keys()):
                    user_id = self._get_user_id_cached(common_name)
                    if not user_id:
                        continue
                    quota_data = self.user_repo.get_user_quota_status(user_id)
                    if not quota_data or quota_data.get('quota_bytes', 0) == 0:
                        continue
                    quota_bytes = quota_data['quota_bytes']
                    bytes_sent, bytes_received = self.traffic_buffer[common_name]
                    current_usage = quota_data.get('bytes_used', 0) + bytes_sent + bytes_received
                    if current_usage >= quota_bytes:
                        self._log(f"QUOTA EXCEEDED: {common_name}")
                        self._disconnect_user(common_name)
        except Exception as e:
            self._log(f"ERROR: Quota check failed: {e}")

    def _get_user_id_cached(self, username: str) -> Optional[int]:
        if username in self.user_cache:
            return self.user_cache[username]
        try:
            user = self.user_repo.get_user_by_username(username)
            if user:
                self.user_cache[username] = user['id']
                return user['id']
        except Exception as e:
            self._log(f"ERROR: User lookup failed for {username}: {e}")
        return None

    def _disconnect_user(self, common_name: str):
        try:
            sessions_to_disconnect = []
            with self.lock:
                for session_key, session in self.sessions.items():
                    if session.common_name == common_name:
                        sessions_to_disconnect.append(session_key)
            for session_key in sessions_to_disconnect:
                client_id = session_key[1]
                # Try to disconnect from both servers
                self._send_command(f"kill {client_id}", "cert")
                self._send_command(f"kill {client_id}", "login")
                self._log(f"Disconnected user {common_name}")
        except Exception as e:
            self._log(f"ERROR: Disconnect user failed: {e}")

    def _cleanup_stale_sessions(self):
        try:
            now = datetime.datetime.now()
            stale_sessions = []
            with self.lock:
                for session_key, session in self.sessions.items():
                    if (now - session.last_seen).total_seconds() > 300:
                        stale_sessions.append(session_key)
                for session_key in stale_sessions:
                    del self.sessions[session_key]
                if len(self.sessions) > MAX_SESSIONS:
                    oldest_sessions = sorted(self.sessions.items(), key=lambda x: x[1].last_seen)
                    for session_key, _ in oldest_sessions[:len(self.sessions) - MAX_SESSIONS]:
                        del self.sessions[session_key]
        except Exception as e:
            self._log(f"ERROR: Session cleanup failed: {e}")

    def _read_events(self):
        try:
            while self.running:
                # Poll status every 5 seconds instead of waiting for events
                self._update_status_cache()
                self._check_quotas_and_enforce()
                time.sleep(5)
        except Exception as e:
            self._log(f"ERROR: Event reading failed: {e}")

    def _parse_state_event(self, line: str):
        try:
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
                elif state == "DISCONNECTED":
                    if session_key in self.sessions:
                        session = self.sessions[session_key]
                        if session.bytes_sent > 0 or session.bytes_received > 0:
                            current_sent, current_received = self.traffic_buffer.get(common_name, (0, 0))
                            self.traffic_buffer[common_name] = (current_sent + session.bytes_sent, current_received + session.bytes_received)
                            self.dirty_users.add(common_name)
                        del self.sessions[session_key]
        except Exception as e:
            self._log(f"ERROR: Parse state event failed: {e}")

    def run_forever(self):
        self.running = True
        self._log("Starting optimized OpenVPN traffic monitor for high-load")
        
        try:
            iteration_count = 0
            while self.running:
                try:
                    iteration_count += 1
                    
                    # Update status every 2 iterations (every 1 second)
                    if iteration_count % 2 == 0:
                        self._update_status_cache()
                    
                    # Always try to flush if there are updates
                    self.smart_flush()
                    
                    # Check quotas every 10 iterations (every 5 seconds)
                    if iteration_count % 10 == 0:
                        self._check_quotas_and_enforce()
                    
                    # Reset counter to prevent overflow
                    if iteration_count > 1000:
                        iteration_count = 0
                    
                    # Sleep 0.5 seconds between iterations
                    time.sleep(0.5)
                    
                except KeyboardInterrupt:
                    self._log("Received interrupt signal, shutting down")
                    break
                except Exception as e:
                    self._log(f"ERROR: Polling failed: {e}")
                    time.sleep(1)
        except Exception as e:
            self._log(f"ERROR: Main loop failed: {e}")
        finally:
            self.disconnect()
            self.db_writer.shutdown()
            self._log("Optimized OpenVPN traffic monitor stopped")

    def _cleanup_caches(self):
        try:
            if len(self.user_cache) > 1000:
                self.user_cache.clear()
            if len(self.status_cache) > 1000:
                self.status_cache.clear()
        except Exception as e:
            self._log(f"ERROR: Cache cleanup failed: {e}")

def main():
    monitor = OptimizedUDSMonitor()
    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        monitor._log("Shutdown requested")
    finally:
        monitor.disconnect()
        monitor.db_writer.shutdown()

if __name__ == "__main__":
    main()
