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

-- JWT AUTHENTICATION SYSTEM TABLES

-- Create admins table (separate from VPN users)
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'reseller',
    token_version INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dynamic permissions system
CREATE TABLE IF NOT EXISTS admin_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE CASCADE,
    UNIQUE(admin_id, permission)
);

-- Token blacklist for immediate revocation
CREATE TABLE IF NOT EXISTS token_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT UNIQUE NOT NULL,
    admin_id INTEGER NOT NULL,
    blacklisted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY(admin_id) REFERENCES admins(id) ON DELETE CASCADE
);

-- Add profile and ownership columns to existing users table
ALTER TABLE users ADD COLUMN profile_token TEXT;
ALTER TABLE users ADD COLUMN profile_last_accessed DATETIME;
ALTER TABLE users ADD COLUMN profile_access_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN created_by INTEGER;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);
CREATE INDEX IF NOT EXISTS idx_admin_permissions_admin_id ON admin_permissions(admin_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_token_id ON token_blacklist(token_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_profile_token_unique ON users(profile_token) WHERE profile_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_created_by ON users(created_by);

-- Auto-cleanup trigger for expired blacklisted tokens
CREATE TRIGGER IF NOT EXISTS cleanup_expired_tokens
AFTER INSERT ON token_blacklist
BEGIN
    DELETE FROM token_blacklist WHERE expires_at < datetime('now');
END;
