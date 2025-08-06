# OpenVPN Manager API Documentation

## Overview

The OpenVPN Manager API provides RESTful endpoints for all functionality available in the CLI interface. This allows you to build web panels, mobile apps, or integrate with other systems.

## Authentication

All API endpoints require authentication using an API key in the request header:

```
X-API-Key: your-api-key-here
```

## Base URL

```
http://your-server:5000/api
```

## Endpoints

### Health Check

#### GET /health
Check if the API server is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "OpenVPN Manager API is running"
}
```

---

## User Management

### Create User

#### POST /users
Create a new VPN user with optional password authentication.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "optional_password"
}
```

**Response (201):**
```json
{
  "message": "User \"john_doe\" created successfully",
  "username": "john_doe",
  "has_certificate": true,
  "has_password": true,
  "certificate_config": "client\ndev tun\n..."
}
```

### Remove User

#### DELETE /users/{username}
Remove a VPN user and all associated credentials.

**Response (200):**
```json
{
  "message": "User \"john_doe\" removed successfully",
  "username": "john_doe"
}
```

### List Users

#### GET /users
List all VPN users with their status and usage information.

**Response (200):**
```json
{
  "message": "Found 2 users",
  "users": [
    {
      "username": "john_doe",
      "status": "active",
      "quota_bytes": 10737418240,
      "bytes_used": 1073741824,
      "usage_percentage": 10.0,
      "auth_types": ["certificate", "login"]
    }
  ]
}
```

### Get User Config

#### GET /users/{username}/config
Get the OpenVPN configuration file for a specific user.

**Response (200):**
```json
{
  "message": "Config retrieved for user \"john_doe\"",
  "username": "john_doe",
  "config": "client\ndev tun\n..."
}
```

### Get Shared Config

#### GET /users/shared-config
Get the shared OpenVPN configuration for username/password authentication.

**Response (200):**
```json
{
  "message": "Shared login-based config retrieved",
  "config": "client\ndev tun\n..."
}
```

### Change User Password

#### PUT /users/{username}/password
Change password for an existing user with password authentication.

**Request Body:**
```json
{
  "new_password": "new_secure_password"
}
```

**Response (200):**
```json
{
  "message": "Password changed successfully for user \"john_doe\"",
  "username": "john_doe"
}
```

**Error (400):**
```json
{
  "error": "Validation error",
  "message": "User 'john_doe' does not have password authentication enabled"
}
```

---

## Quota Management

### Set User Quota

#### PUT /quota/{username}
Set data quota for a specific user.

**Request Body:**
```json
{
  "quota_gb": 10.5
}
```

**Response (200):**
```json
{
  "message": "Quota set successfully for user \"john_doe\"",
  "username": "john_doe",
  "quota_gb": 10.5,
  "quota_bytes": 11274289152,
  "quota_human": "10.50 GB"
}
```

### Get User Status

#### GET /quota/{username}
Get detailed traffic status and quota information for a specific user.

**Response (200):**
```json
{
  "message": "Status retrieved for user \"john_doe\"",
  "status": {
    "username": "john_doe",
    "quota_bytes": 10737418240,
    "quota_human": "10.00 GB",
    "bytes_used": 1073741824,
    "bytes_used_human": "1.00 GB",
    "usage_percentage": 10.0,
    "remaining_bytes": 9663676416,
    "remaining_human": "9.00 GB",
    "is_over_quota": false
  }
}
```

---

## System Management

### Create Backup

#### POST /system/backup
Create an encrypted backup of the entire VPN system.

**Request Body:**
```json
{
  "password": "backup_password",
  "backup_dir": "~/backups"
}
```

**Response (200):**
```json
{
  "message": "Backup created successfully",
  "backup_file": "/home/user/backups/system_backup_2024-01-15_14-30-25.tar.gz.gpg",
  "backup_directory": "/home/user/backups"
}
```

### Restore System

#### POST /system/restore
Restore the VPN system from an encrypted backup file.

**Request Body:**
```json
{
  "backup_path": "/path/to/backup.tar.gz.gpg",
  "password": "backup_password"
}
```

**Response (200):**
```json
{
  "message": "System restore completed successfully",
  "backup_path": "/path/to/backup.tar.gz.gpg"
}
```

### Uninstall VPN

#### DELETE /system/uninstall
Completely uninstall the OpenVPN system and remove all users.

**Request Body:**
```json
{
  "confirm": true
}
```

**Response (200):**
```json
{
  "message": "OpenVPN system uninstalled successfully",
  "users_removed": 3,
  "removed_users": ["user1", "user2", "user3"]
}
```

### System Status

#### GET /system/status
Get overall system status and statistics.

**Response (200):**
```json
{
  "message": "System status retrieved successfully",
  "installed": true,
  "users_count": 5,
  "settings": {
    "public_ip": "203.0.113.1",
    "cert_port": "1194",
    "cert_proto": "udp",
    "login_port": "1195",
    "login_proto": "udp",
    "dns": "3",
    "cipher": "AES-256-GCM"
  }
}
```

---

## Error Responses

All endpoints may return these standard error responses:

### 400 Bad Request
```json
{
  "error": "Validation error",
  "message": "Username is required"
}
```

### 401 Unauthorized
```json
{
  "error": "API key required",
  "message": "Please provide X-API-Key header"
}
```

### 404 Not Found
```json
{
  "error": "User not found",
  "message": "User 'nonexistent' not found"
}
```

### 409 Conflict
```json
{
  "error": "User already exists",
  "message": "User 'john_doe' already exists"
}
```

### 500 Internal Server Error
```json
{
  "error": "VPN Manager error",
  "message": "Certificate generation failed"
}
```

---

## Deployment

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Deploy API Service
```bash
sudo ./scripts/deploy_api.sh
```

### 3. Check Service Status
```bash
sudo systemctl status openvpn-api.service
```

### 4. View Logs
```bash
sudo journalctl -u openvpn-api.service -f
```

---

## Example Usage

### Python Example
```python
import requests

API_BASE = "http://your-server:5000/api"
API_KEY = "your-api-key"

headers = {"X-API-Key": API_KEY}

# Create a user
response = requests.post(f"{API_BASE}/users", 
    json={"username": "testuser", "password": "testpass"},
    headers=headers
)
print(response.json())

# List users
response = requests.get(f"{API_BASE}/users", headers=headers)
print(response.json())

# Change user password
response = requests.put(f"{API_BASE}/users/testuser/password", 
    json={"new_password": "newpassword123"},
    headers=headers
)
print(response.json())
```

### cURL Example
```bash
# Health check
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/health

# Create user
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' \
  http://localhost:5000/api/users

# List users
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/users

# Change user password
curl -X PUT \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "newpassword123"}' \
  http://localhost:5000/api/users/testuser/password
```

---

## Security Notes

1. **API Key**: Keep your API key secure and rotate it regularly
2. **HTTPS**: Use HTTPS in production environments
3. **Firewall**: Restrict API access to trusted IP addresses
4. **Root Access**: The API requires root privileges for OpenVPN operations
5. **Backup Passwords**: Use strong passwords for system backups