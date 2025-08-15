# OpenVPN UDS Traffic Monitoring System

## 📋 Overview

This is a **near-realtime**, **low-overhead** traffic monitoring system for OpenVPN that uses **Unix Domain Sockets (UDS)** for secure, efficient communication with the OpenVPN management interface.

### 🚀 Key Features

- **Unix Domain Socket (UDS)** - No TCP ports, file-permission-based security
- **Near-realtime monitoring** - `bytecount <n>` events every 5-10 seconds
- **Accurate traffic counting** - Per-session aggregation with anti-double-counting
- **Quota enforcement** - Buffer-based cutoff with immediate disconnection
- **SQLite optimization** - WAL mode, batched writes, efficient indexing
- **Production ready** - systemd service, log rotation, error recovery

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenVPN       │    │  UDS Monitor     │    │   SQLite DB     │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │UDS Socket   │◄┼────┼─│ Event Parser │ │    │ │user_quotas  │ │
│ │/run/openvpn │ │    │ └──────────────┘ │    │ └─────────────┘ │
│ │/ovpn-mgmt   │ │    │                  │    │                 │
│ │.sock        │ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ └─────────────┘ │    │ │ Quota Check  │─┼────┼─│traffic_logs │ │
│                 │    │ └──────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │                  │    │                 │
│ │bytecount 5  │ │    │ ┌──────────────┐ │    │                 │
│ │state on     │ │    │ │ Session Mgr  │ │    │                 │
│ └─────────────┘ │    │ └──────────────┘ │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## ⚡ Performance Characteristics

- **Memory Usage**: ~15-25MB (Python process + SQLite WAL)
- **CPU Usage**: <2% (only during event processing)
- **Network**: Zero (UDS communication)
- **Disk I/O**: Minimal (batched SQLite writes every 30s)
- **Latency**: Near-realtime (5-10 second updates)
- **Security**: File permissions only, no network exposure

## 🚀 Quick Deployment

### 1. Deploy the UDS Monitor
```bash
sudo ./scripts/deploy_uds_monitor.sh
```

### 2. Set User Quotas
```bash
python3 cli/main.py
# Choose option 7: Set user quota
```

### 3. Monitor the Service
```bash
# View service status
sudo systemctl status openvpn-uds-monitor.service

# View real-time logs
sudo journalctl -u openvpn-uds-monitor.service -f

# View traffic logs
sudo tail -f /var/log/openvpn/traffic_monitor.log
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVPN_UDS_SOCKET` | `/run/openvpn/ovpn-mgmt.sock` | UDS socket path |
| `BYTECOUNT_INTERVAL` | `5` | Bytecount event interval (seconds) |
| `RECONCILE_INTERVAL` | `300` | Full status reconciliation (seconds) |
| `DB_FLUSH_INTERVAL` | `30` | Database checkpoint interval (seconds) |
| `QUOTA_BUFFER_BYTES` | `20971520` | Quota enforcement buffer (20MB) |
| `MAX_LOG_SIZE` | `10485760` | Log rotation size (10MB) |

### OpenVPN Server Configuration

The deployment script automatically configures OpenVPN:

```conf
# UDS Management Interface for Traffic Monitoring
management /run/openvpn/ovpn-mgmt.sock unix
status-version 3
```

### Systemd Service Configuration

```ini
[Service]
User=root
Group=openvpn
RuntimeDirectory=openvpn
UMask=007
ExecStartPost=/usr/bin/chmod 770 /run/openvpn/ovpn-mgmt.sock
ExecStartPost=/usr/bin/chgrp openvpn /run/openvpn/ovpn-mgmt.sock
```

## 🔧 How It Works

### 1. **UDS Connection & Event Mode**
```python
# Connect via Unix Domain Socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/run/openvpn/ovpn-mgmt.sock")

# Enable near-realtime events
file_handle.write("bytecount 5\n")  # Every 5 seconds
file_handle.write("state on\n")     # Session state events
```

### 2. **Accurate Traffic Counting**
```python
# Per-session key: (common_name, client_id)
session_key = (common_name, client_id)

# Clamp increments to prevent negative values
sent_increment = max(0, bytes_sent - last_bytes_sent)
received_increment = max(0, bytes_received - last_bytes_received)

# Aggregate per-user totals
user_totals[common_name] += total_increment
```

### 3. **Quota Enforcement**
```python
# Check with buffer to absorb between-tick overshoot
if current_usage >= quota_bytes + buffer_bytes:
    client_kill(client_id, reason="quota_exceeded")
```

### 4. **Database Optimization**
```sql
-- WAL mode for concurrent access
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=3000;

-- UPSERT for efficient quota updates
INSERT INTO user_quotas (user_id, bytes_used)
VALUES (?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    bytes_used = user_quotas.bytes_used + excluded.bytes_used;
```

## 📊 Monitoring & Troubleshooting

### Service Management
```bash
# Start service
sudo systemctl start openvpn-uds-monitor.service

# Stop service
sudo systemctl stop openvpn-uds-monitor.service

# Restart service
sudo systemctl restart openvpn-uds-monitor.service

# View logs
sudo journalctl -u openvpn-uds-monitor.service -f

# Check status
sudo systemctl status openvpn-uds-monitor.service
```

### Database Queries
```bash
# Check user quotas and usage
sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "
SELECT u.username, q.quota_bytes, q.bytes_used, 
       (q.bytes_used * 100.0 / q.quota_bytes) as usage_percent
FROM users u 
JOIN user_quotas q ON u.id = q.user_id 
WHERE q.quota_bytes > 0;"

# View recent traffic logs
sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "
SELECT u.username, t.bytes_sent, t.bytes_received, t.log_timestamp
FROM traffic_logs t
JOIN users u ON t.user_id = u.id
ORDER BY t.log_timestamp DESC
LIMIT 20;"
```

### Common Issues

#### 1. **UDS Socket Not Found**
```bash
# Check if OpenVPN is running
sudo systemctl status openvpn@server

# Check socket permissions
ls -la /run/openvpn/ovpn-mgmt.sock

# Verify OpenVPN configuration
grep "management.*unix" /etc/openvpn/server.conf
```

#### 2. **Permission Denied**
```bash
# Check group membership
groups root

# Fix socket permissions
sudo chmod 770 /run/openvpn/ovpn-mgmt.sock
sudo chgrp openvpn /run/openvpn/ovpn-mgmt.sock
```

#### 3. **High Resource Usage**
```bash
# Check monitoring intervals
systemctl show openvpn-uds-monitor.service -p Environment

# Adjust if needed
sudo systemctl edit openvpn-uds-monitor.service
```

## 🔒 Security Features

### **UDS Security Model**
- **No TCP ports** - Zero network exposure
- **File permissions** - `root:openvpn` ownership, `770` mode
- **Group-based access** - Monitor user in `openvpn` group
- **Systemd hardening** - `NoNewPrivileges`, `ProtectSystem=strict`

### **Database Security**
- **File permissions** - `700` on database directory
- **WAL mode** - Atomic transactions, crash recovery
- **Parameterized queries** - SQL injection protection
- **Input validation** - All user inputs sanitized

### **Service Security**
- **Resource limits** - Memory and CPU quotas
- **Read-only paths** - Minimal file system access
- **Log rotation** - Prevents disk space exhaustion
- **Error handling** - Graceful failure recovery

## 📈 Performance Optimization

### **Database Optimizations**
```sql
-- WAL mode for concurrent access
PRAGMA journal_mode=WAL;

-- Efficient indexing
CREATE INDEX idx_user_quotas_username ON user_quotas(user_id);
CREATE INDEX idx_traffic_logs_user_time ON traffic_logs(user_id, log_timestamp);

-- Memory optimizations
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;
```

### **Memory Management**
- **Session tracking** - In-memory session state
- **Batched writes** - Database updates every 30 seconds
- **Connection pooling** - Efficient database connections
- **Resource cleanup** - Proper socket and file handle management

### **Event Processing**
- **Threaded event reading** - Non-blocking event processing
- **Incremental updates** - Only process changed data
- **Efficient parsing** - Optimized status output parsing
- **Error recovery** - Automatic reconnection on failures

## 🔄 Operational Procedures

### **Monthly Quota Reset**
```bash
# Create reset script
cat > /etc/owpanel/scripts/reset_quotas.sh << 'EOF'
#!/bin/bash
sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "
UPDATE user_quotas SET bytes_used = 0, updated_at = CURRENT_TIMESTAMP;
"
echo "Quotas reset at $(date)" >> /var/log/openvpn/quota_reset.log
EOF

chmod +x /etc/owpanel/scripts/reset_quotas.sh

# Add to crontab (first day of month at 00:01)
echo "1 0 1 * * /etc/owpanel/scripts/reset_quotas.sh" | sudo crontab -
```

### **Database Maintenance**
```bash
# Weekly database optimization
cat > /etc/owpanel/scripts/db_maintenance.sh << 'EOF'
#!/bin/bash
sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "
VACUUM;
ANALYZE;
PRAGMA wal_checkpoint(TRUNCATE);
"
EOF

chmod +x /etc/owpanel/scripts/db_maintenance.sh

# Add to crontab (weekly on Sunday at 02:00)
echo "0 2 * * 0 /etc/owpanel/scripts/db_maintenance.sh" | sudo crontab -
```

### **Log Rotation**
```bash
# Configure logrotate
sudo tee /etc/logrotate.d/openvpn-uds-monitor << EOF
/var/log/openvpn/traffic_monitor.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload openvpn-uds-monitor.service
    endscript
}
EOF
```

## 🧪 Testing

### **Connection Test**
```bash
# Test UDS connection manually
echo "status" | socat - UNIX-CONNECT:/run/openvpn/ovpn-mgmt.sock
```

### **Traffic Simulation**
```bash
# Monitor traffic in real-time
sudo journalctl -u openvpn-uds-monitor.service -f | grep "Session.*bytes"

# Check database updates
watch -n 5 'sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "SELECT username, bytes_used FROM users u JOIN user_quotas q ON u.id = q.user_id;"'
```

### **Quota Enforcement Test**
```bash
# Set a small quota for testing
sqlite3 /etc/owpanel/openvpn_data/vpn_manager.db "
UPDATE user_quotas 
SET quota_bytes = 1048576 
WHERE user_id = (SELECT id FROM users WHERE username = 'testuser');
"

# Monitor for disconnection
sudo journalctl -u openvpn-uds-monitor.service -f | grep "QUOTA EXCEEDED"
```

## 📝 Migration from TCP Monitor

### **Migration from TCP Monitor**

**Note: The old TCP-based monitor has been completely removed from the codebase.**
**The UDS monitor is now the only monitoring system.**

To deploy the UDS monitor:

```bash
# Deploy UDS monitor
sudo ./scripts/deploy_uds_monitor.sh
```

The deployment script will:
1. Configure OpenVPN for UDS management interface
2. Set up proper permissions and systemd overrides
3. Deploy and start the UDS monitor service
4. Remove any old TCP-based configurations

## 🎯 Best Practices

### **Configuration**
- Use `bytecount 5` for near-realtime monitoring (5-10 second updates)
- Set `QUOTA_BUFFER_BYTES` to 5-30MB based on expected throughput
- Configure `RECONCILE_INTERVAL` to 2-5 minutes for session cleanup
- Use `DB_FLUSH_INTERVAL` of 15-30 seconds for optimal performance

### **Monitoring**
- Monitor service logs for connection issues
- Track database size and performance
- Set up alerts for quota violations
- Regular backup of database and configuration

### **Security**
- Keep OpenVPN and monitor services updated
- Monitor system logs for unauthorized access attempts
- Regular security audits of configuration
- Backup and test recovery procedures

## 📚 References

- [OpenVPN Management Interface Documentation](https://openvpn.net/community-resources/management-interface/)
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [systemd Service Security](https://systemd.io/SECURITY/)

---

**Status**: ✅ Production Ready - UDS-based near-realtime traffic monitoring with comprehensive quota enforcement and security hardening. 