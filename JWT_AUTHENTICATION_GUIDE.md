# 🔐 JWT Authentication System - Complete Guide

## 📋 Overview

This OpenVPN Manager now includes an **enterprise-grade JWT authentication system** that replaces the simple API key authentication with comprehensive security features:

- **JWT-based authentication** with token versioning
- **Real-time permission management** with role-based access control
- **Token blacklisting** for immediate revocation
- **Public profile system** with secure token access
- **Rate limiting** and security controls
- **Enhanced admin management** with reseller isolation

## 🚀 Quick Start

### Installation

Use the enhanced deployment script:

```bash
sudo chmod +x deploy_jwt.sh
sudo ./deploy_jwt.sh
```

The installer will:
1. Set up the complete OpenVPN system
2. Create JWT authentication database
3. Configure the first admin user
4. Start the API server with JWT authentication

### First Login

After installation, you'll receive:
- **Admin Username**: Your chosen username
- **Admin Password**: Generated secure password
- **API URL**: `http://your-server:port`

## 🔑 Authentication Flow

### 1. Login
```bash
curl -X POST http://your-server:port/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

Response:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "role": "admin",
  "expires_in": 86400,
  "username": "admin"
}
```

### 2. Using the Token
Include the JWT token in the Authorization header:

```bash
curl -X GET http://your-server:port/api/users \
  -H "Authorization: Bearer your-jwt-token"
```

### 3. Logout
```bash
curl -X POST http://your-server:port/api/auth/logout \
  -H "Authorization: Bearer your-jwt-token"
```

## 👥 User Management

### Admin Roles

**Admin**: Full system access
- Manage all VPN users
- Create/manage other admins
- System configuration
- All permissions

**Reseller**: Limited access
- Manage only their created VPN users
- Generate profile links for their users
- View quota and reports for their users
- Cannot manage other admins

### Creating Admins

```bash
curl -X POST http://your-server:port/api/admins \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "reseller1",
    "password": "secure-password",
    "role": "reseller"
  }'
```

### Managing Permissions

```bash
# Grant permissions
curl -X POST http://your-server:port/api/permissions/admins/2 \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "permissions": ["users:create", "users:read", "quota:manage"]
  }'

# Revoke permissions
curl -X DELETE http://your-server:port/api/permissions/admins/2 \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "permissions": ["system:config"]
  }'
```

## 📊 Available Permissions

| Permission | Description |
|------------|-------------|
| `users:create` | Create new VPN users |
| `users:read` | View VPN user information |
| `users:update` | Modify VPN user settings |
| `users:delete` | Delete VPN users |
| `admins:create` | Create new admin users |
| `admins:read` | View admin information |
| `admins:update` | Modify admin settings |
| `admins:delete` | Delete admin users |
| `permissions:grant` | Grant permissions to admins |
| `permissions:revoke` | Revoke permissions from admins |
| `system:config` | System configuration access |
| `quota:manage` | Manage user quotas |
| `reports:view` | View system reports |
| `profile:generate` | Generate profile links |
| `profile:revoke` | Revoke profile access |
| `tokens:revoke` | Force logout other admins |

## 🔗 Public Profile System

### Generate Profile Link

```bash
curl -X POST http://your-server:port/api/profile/users/123/profile-link \
  -H "Authorization: Bearer token-with-profile-generate-permission"
```

Response:
```json
{
  "profile_token": "abc123...",
  "profile_url": "http://your-server:port/profile/abc123...",
  "existing": false
}
```

### Public Access (No Authentication)

Users can access their profile via:
- **HTML View**: `http://your-server:port/profile/abc123...`
- **JSON Data**: `http://your-server:port/profile/abc123.../data`
- **VPN Config**: `http://your-server:port/profile/abc123.../config.ovpn`

### Profile Features

- Real-time quota information
- Connection status
- Download VPN configuration
- Access statistics
- Mobile-friendly interface

## 🛡️ Security Features

### Token Security
- **24-hour expiry** with automatic cleanup
- **Unique token IDs** for tracking and revocation
- **Token versioning** for instant invalidation
- **Blacklist system** with memory + database persistence

### Rate Limiting
- **Login attempts**: 5 per 10 minutes per IP
- **Profile access**: 60 requests per minute per IP
- **Admin operations**: 100 requests per minute per admin

### Access Control
- **Role-based isolation**: Resellers only see their users
- **Real-time permission checking**: No cached permissions
- **Creator tracking**: Track which admin created each user

## 📡 API Endpoints

### Authentication
- `POST /api/auth/login` - Admin login
- `POST /api/auth/logout` - Logout current session
- `GET /api/auth/verify` - Verify token validity
- `PUT /api/auth/change-password` - Change own password

### Admin Management
- `GET /api/admins` - List all admins
- `POST /api/admins` - Create new admin
- `GET /api/admins/{id}` - Get admin details
- `PUT /api/admins/{id}` - Update admin
- `DELETE /api/admins/{id}` - Delete admin
- `POST /api/admins/{id}/logout` - Force logout admin

### Permission Management
- `GET /api/permissions/available` - List available permissions
- `GET /api/permissions/admins/{id}` - Get admin permissions
- `POST /api/permissions/admins/{id}` - Grant permissions
- `DELETE /api/permissions/admins/{id}` - Revoke permissions

### VPN User Management
- `GET /api/users` - List users (filtered by admin role)
- `POST /api/users` - Create VPN user
- `DELETE /api/users/{username}` - Delete VPN user
- `GET /api/users/{username}/config` - Get user config
- `PUT /api/users/{username}/password` - Change user password

### Profile Management
- `POST /api/profile/users/{id}/profile-link` - Generate profile link
- `GET /api/profile/users/{id}/profile-link` - Get existing link
- `PUT /api/profile/users/{id}/profile-link` - Regenerate link
- `DELETE /api/profile/users/{id}/profile-link` - Revoke access
- `GET /api/profile/users/{id}/profile-stats` - Access statistics

### Public Profiles (No Auth)
- `GET /profile/{token}` - Public profile view
- `GET /profile/{token}/data` - Profile data API
- `GET /profile/{token}/config.ovpn` - Download VPN config

## 🔧 Configuration

### Environment Variables

The system uses environment variables stored in `/etc/openvpn-manager/.env`:

```bash
ADMIN_USERNAME=admin
API_PORT=5000
JWT_SECRET=base64-encoded-secret-key
DATABASE_PATH=/etc/openvpn-manager/database.db
API_SECRET_KEY=flask-secret-key
FLASK_ENV=production
```

### Service Management

```bash
# Control API service
systemctl start openvpn-api
systemctl stop openvpn-api
systemctl restart openvpn-api
systemctl status openvpn-api

# View logs
journalctl -u openvpn-api -f
```

## 🔍 Troubleshooting

### Common Issues

**1. Token Validation Errors**
- Check JWT_SECRET environment variable
- Verify token hasn't expired (24 hours)
- Ensure token wasn't blacklisted

**2. Permission Denied**
- Check admin role and permissions
- Verify token is valid and not expired
- For resellers, ensure accessing own users only

**3. Rate Limiting**
- Wait for rate limit window to expire
- Check IP-based vs admin-based limits
- Monitor logs for rate limit violations

**4. Database Issues**
- Check database file permissions (644)
- Verify database schema is up to date
- Check disk space for database operations

### Debug Commands

```bash
# Check API health
curl http://localhost:5000/api/health

# Verify token (replace with actual token)
curl -X GET http://localhost:5000/api/auth/verify \
  -H "Authorization: Bearer your-token"

# Check admin permissions
curl -X GET http://localhost:5000/api/permissions/admins/1 \
  -H "Authorization: Bearer admin-token"

# View service logs
journalctl -u openvpn-api --since "1 hour ago"
```

## 📈 Monitoring

### Key Metrics to Monitor

1. **Authentication Success/Failure Rates**
2. **Token Blacklist Size**
3. **Rate Limiting Violations**
4. **Profile Access Patterns**
5. **Admin Permission Changes**

### Log Locations

- **API Logs**: `journalctl -u openvpn-api`
- **Database**: `/etc/openvpn-manager/database.db`
- **Environment**: `/etc/openvpn-manager/.env`

## 🔄 Migration from API Key

The JWT system completely replaces the API key authentication:

1. **Old API Key endpoints removed**
2. **All routes now require JWT authentication**
3. **Enhanced security with permissions**
4. **Backward compatibility**: None (complete upgrade)

### Migration Steps

1. Deploy new system using `deploy_jwt.sh`
2. Create admin accounts for existing API key users
3. Update client applications to use JWT authentication
4. Test all functionality with new authentication
5. Remove old API key configurations

## 🎯 Best Practices

### Security
- **Rotate JWT secrets** periodically
- **Monitor failed login attempts**
- **Use HTTPS** in production
- **Limit admin accounts** to necessary personnel
- **Regular permission audits**

### Operations
- **Monitor token blacklist size**
- **Set up log rotation**
- **Regular database backups**
- **Monitor rate limiting metrics**
- **Document admin role assignments**

### Development
- **Use environment-specific configurations**
- **Test permission boundaries**
- **Validate input on all endpoints**
- **Handle errors gracefully**
- **Log security events**

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review API endpoint responses
3. Check service logs
4. Verify environment configuration
5. Test with minimal examples

The JWT authentication system provides enterprise-grade security while maintaining the simplicity and performance requirements of the OpenVPN Manager.