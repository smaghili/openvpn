-- Database schema for VPN Manager (SQLite)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    protocol TEXT NOT NULL,         -- 'openvpn', ...
    auth_type TEXT NOT NULL,        -- 'certificate', ...
    cert_pem TEXT,
    key_pem TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- NEW TABLES FOR TRAFFIC MONITORING

-- Stores the quota and total usage for each user
CREATE TABLE IF NOT EXISTS user_quotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    -- Quota in bytes. 0 means unlimited.
    quota_bytes INTEGER NOT NULL DEFAULT 0,
    -- Total bytes used so far in the current period
    bytes_used INTEGER NOT NULL DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores periodic snapshots of traffic for historical analysis
CREATE TABLE IF NOT EXISTS traffic_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL,
    bytes_received INTEGER NOT NULL,
    -- When this record was logged
    log_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- A trigger to automatically add a quota entry for a new user.
CREATE TRIGGER IF NOT EXISTS after_user_insert
AFTER INSERT ON users
BEGIN
    INSERT INTO user_quotas (user_id) VALUES (new.id);
END;
