#!/bin/bash
# Enhanced deployment script for VPN Manager with JWT Authentication System
# This script sets up the complete system with enterprise-grade security

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="openvpn"
ENV_FILE="/etc/openvpn-manager/.env"
# Use the same database path that the application uses (will be set dynamically)
DB_PATH=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Functions ---

function print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run with root privileges. Please use 'sudo'."
        exit 1
    fi
}

function validate_input() {
    local input="$1"
    local pattern="$2"
    local error_msg="$3"
    
    if [[ ! $input =~ $pattern ]]; then
        print_error "$error_msg"
        return 1
    fi
    return 0
}

function check_port_available() {
    local port="$1"
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_error "Port $port is already in use."
        return 1
    fi
    return 0
}

function generate_secure_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-16
}

function generate_jwt_secret() {
    openssl rand -base64 64 | tr -d '\n' | tr -d '=+/'
}

function get_admin_credentials() {
    print_header "Admin Account Setup"
    
    # Get admin username with validation
    while true; do
        echo -n "Enter admin username (3-50 chars, default: admin): "
        read ADMIN_USERNAME
        ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
        
        if validate_input "$ADMIN_USERNAME" "^[a-zA-Z0-9_.-]{3,50}$" "Username must be 3-50 characters, alphanumeric plus ._- only."; then
            break
        fi
    done
    
    # Get admin password with validation
    while true; do
        echo -n "Enter admin password (min 8 chars, leave empty for auto-generated): "
        read -s ADMIN_PASSWORD
        echo ""
        
        if [ -z "$ADMIN_PASSWORD" ]; then
            ADMIN_PASSWORD=$(generate_secure_password)
            print_success "Generated secure password: $ADMIN_PASSWORD"
            echo -e "${YELLOW}IMPORTANT: Save this password securely! It cannot be recovered.${NC}"
            echo -n "Press Enter to continue..."
            read
            break
        elif [ ${#ADMIN_PASSWORD} -ge 8 ]; then
            echo -n "Confirm password: "
            read -s ADMIN_PASSWORD_CONFIRM
            echo ""
            
            if [ "$ADMIN_PASSWORD" = "$ADMIN_PASSWORD_CONFIRM" ]; then
                break
            else
                print_error "Passwords do not match."
            fi
        else
            print_error "Password must be at least 8 characters."
        fi
    done
}

function get_api_port() {
    print_header "API Server Configuration"
    
    while true; do
        echo -n "Enter API port (1024-65535, default: random): "
        read API_PORT
        
        if [ -z "$API_PORT" ]; then
            API_PORT=$(shuf -i 3000-9999 -n 1)
            print_success "Generated port: $API_PORT"
            break
        elif validate_input "$API_PORT" "^[0-9]+$" "Port must be numeric." && 
             [ "$API_PORT" -ge 1024 ] && [ "$API_PORT" -le 65535 ]; then
            if check_port_available "$API_PORT"; then
                break
            fi
        else
            print_error "Invalid port. Must be between 1024-65535."
        fi
    done
}

function setup_environment() {
    print_header "Environment Configuration"
    
    # Create secure directory
    mkdir -p /etc/openvpn-manager
    chmod 700 /etc/openvpn-manager
    
    # Generate JWT secret
    JWT_SECRET=$(generate_jwt_secret)
    
    # Create environment file
    cat > "$ENV_FILE" << EOF
# OpenVPN Manager JWT Authentication Configuration
ADMIN_USERNAME=$ADMIN_USERNAME
API_PORT=$API_PORT
JWT_SECRET=$JWT_SECRET
DATABASE_PATH=$DB_PATH
API_SECRET_KEY=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
FLASK_ENV=production
EOF
    
    # Set secure permissions
    chmod 600 "$ENV_FILE"
    chown root:root "$ENV_FILE"
    
    print_success "Environment configuration created"
}

function setup_database() {
    print_header "Database Setup"
    
    # Ensure database directory exists
    mkdir -p "$(dirname "$DB_PATH")"
    
    # Check if system is already installed
    if [ -f "$DB_PATH" ]; then
        print_warning "Database already exists. Checking admin user..."
        
        # Check if admin user exists
        ADMIN_EXISTS=$(./venv/bin/python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('$DB_PATH')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM admins WHERE username = ?', ('$ADMIN_USERNAME',))
    count = cursor.fetchone()[0]
    conn.close()
    print(count)
except Exception as e:
    print(0)
")
        
        if [ "$ADMIN_EXISTS" -gt 0 ]; then
            echo -e "${YELLOW}Admin user '$ADMIN_USERNAME' already exists.${NC}"
            echo -n "Update admin password? (y/N): "
            read -r update_admin
            
            if [[ ! "$update_admin" =~ ^[Yy]$ ]]; then
                print_success "Database setup skipped - using existing configuration"
                return
            fi
        fi
    fi
    
    # Hash admin password
    PASSWORD_HASH=$(./venv/bin/python3 -c "
import bcrypt
import sys
password = '$ADMIN_PASSWORD'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode('utf-8'))
")
    
    # Create database and admin user
    JWT_SECRET_VAR="$JWT_SECRET" DB_PATH_VAR="$DB_PATH" ADMIN_USERNAME_VAR="$ADMIN_USERNAME" PASSWORD_HASH_VAR="$PASSWORD_HASH" ./venv/bin/python3 << 'EOF'
import sqlite3
import sys
import os

# Get variables from environment (passed from shell)
JWT_SECRET = os.environ.get('JWT_SECRET_VAR', '')
DB_PATH = os.environ.get('DB_PATH_VAR', '')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME_VAR', '')
PASSWORD_HASH = os.environ.get('PASSWORD_HASH_VAR', '')

print(f"Setting up database at: {DB_PATH}")
print(f"Creating admin user: {ADMIN_USERNAME}")

# Create database connection
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Run schema creation
with open('database.sql', 'r') as f:
    schema = f.read()
    cursor.executescript(schema)

# Check if admin exists
cursor.execute('SELECT id FROM admins WHERE username = ?', (ADMIN_USERNAME,))
existing_admin = cursor.fetchone()

if existing_admin:
    admin_id = existing_admin[0]
    print(f"Admin user exists, updating password...")
    cursor.execute(
        'UPDATE admins SET password_hash = ?, token_version = token_version + 1 WHERE id = ?', 
        (PASSWORD_HASH, admin_id)
    )
    # Clear existing permissions first
    cursor.execute('DELETE FROM admin_permissions WHERE admin_id = ?', (admin_id,))
else:
    print(f"Creating new admin user...")
    cursor.execute(
        'INSERT INTO admins (username, password_hash, role) VALUES (?, ?, ?)', 
        (ADMIN_USERNAME, PASSWORD_HASH, 'admin')
    )
    admin_id = cursor.lastrowid

# Grant all permissions to admin
permissions = [
    'users:create', 'users:read', 'users:update', 'users:delete',
    'admins:create', 'admins:read', 'admins:update', 'admins:delete',
    'permissions:grant', 'permissions:revoke',
    'system:config', 'quota:manage', 'reports:view',
    'profile:generate', 'profile:revoke', 'tokens:revoke'
]

for permission in permissions:
    try:
        cursor.execute(
            'INSERT INTO admin_permissions (admin_id, permission) VALUES (?, ?)',
            (admin_id, permission)
        )
    except Exception:
        # Permission table might not exist, skip
        pass

conn.commit()
conn.close()
print(f"Database setup completed. Admin user ID: {admin_id}")
EOF
    
    # Set database permissions
    chmod 644 "$DB_PATH"
    chown root:root "$DB_PATH"
    
    print_success "Database setup completed"
}

function create_api_service() {
    print_header "API Service Setup"
    
    # Create systemd service file
    cat > /etc/systemd/system/openvpn-api.service << EOF
[Unit]
Description=OpenVPN Manager API Server with JWT Authentication
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$(pwd)
Environment=PYTHONPATH=$(pwd)
EnvironmentFile=$ENV_FILE
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/api/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable openvpn-api
    
    print_success "API service created and enabled"
}

function install_dependencies() {
    print_header "Installing Dependencies"
    
    echo "Installing system packages..."
    apt-get update
    apt-get install -y git python3-venv python3-pip openssl netstat-nat
    
    print_success "System packages installed"
}

function setup_project() {
    print_header "Project Setup"
    
    if [ -d "$PROJECT_DIR" ]; then
        echo "Project directory exists. Fetching latest version..."
        cd "$PROJECT_DIR"
        git reset --hard HEAD
        git pull origin main
    else
        echo "Cloning project repository..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    # Set database path after entering project directory
    DB_PATH="$(pwd)/openvpn_data/vpn_manager.db"
    
    echo "Setting up Python environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Set execute permissions
    chmod +x cli/main.py api/app.py scripts/*.py 2>/dev/null || true
    
    print_success "Project setup completed"
}

function setup_openvpn() {
    print_header "OpenVPN Installation"
    
    export PROJECT_ROOT="$(pwd)"
    
    # Run CLI installer for OpenVPN setup
    if sudo PROJECT_ROOT="$PROJECT_ROOT" INSTALL_ONLY=1 ./venv/bin/python -m cli.main; then
        print_success "OpenVPN installation completed"
    else
        print_error "OpenVPN installation failed"
        exit 1
    fi
}

function start_services() {
    print_header "Starting Services"
    
    # Start API service
    systemctl start openvpn-api
    
    # Wait for service to start
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet openvpn-api; then
        print_success "API service started successfully"
        
        # Test API health
        sleep 2
        if curl -f http://localhost:$API_PORT/api/health >/dev/null 2>&1; then
            print_success "API health check passed"
        else
            print_warning "API health check failed, but service is running"
        fi
    else
        print_error "Failed to start API service"
        systemctl status openvpn-api
        journalctl -u openvpn-api --no-pager -n 20
        exit 1
    fi
}

function show_completion_info() {
    print_header "Installation Complete"
    
    echo -e "${GREEN}🎉 OpenVPN Manager with JWT Authentication has been successfully installed!${NC}\n"
    
    echo -e "${BLUE}=== AUTHENTICATION DETAILS ===${NC}"
    echo -e "Admin Username: ${YELLOW}$ADMIN_USERNAME${NC}"
    echo -e "Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}"
    echo -e "API URL: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT${NC}"
    echo -e "Web Panel: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT${NC}"
    echo -e "Health Check: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT/api/health${NC}"
    echo -e "Database Path: ${YELLOW}$DB_PATH${NC}"
    
    echo -e "\n${BLUE}=== API ENDPOINTS ===${NC}"
    echo -e "Login: POST /api/auth/login"
    echo -e "Users: GET /api/users (requires authentication)"
    echo -e "Admin Panel: GET /api/admins (admin only)"
    echo -e "Documentation: Available via API endpoints"
    
    echo -e "\n${BLUE}=== SECURITY FEATURES ===${NC}"
    echo -e "✅ JWT-based authentication with token versioning"
    echo -e "✅ Real-time permission checking"
    echo -e "✅ Token blacklisting for immediate revocation"
    echo -e "✅ Rate limiting on all endpoints"
    echo -e "✅ Role-based access control (Admin/Reseller)"
    echo -e "✅ Public profile system with secure tokens"
    
    echo -e "\n${BLUE}=== IMPORTANT NOTES ===${NC}"
    echo -e "${RED}🔒 SAVE THESE CREDENTIALS SECURELY!${NC}"
    echo -e "The admin password cannot be recovered if lost."
    echo -e "Environment file: $ENV_FILE"
    echo -e "Database file: $DB_PATH"
    
    echo -e "\n${BLUE}=== SERVICE MANAGEMENT ===${NC}"
    echo -e "Start API: ${YELLOW}systemctl start openvpn-api${NC}"
    echo -e "Stop API: ${YELLOW}systemctl stop openvpn-api${NC}"
    echo -e "View Logs: ${YELLOW}journalctl -u openvpn-api -f${NC}"
    echo -e "Service Status: ${YELLOW}systemctl status openvpn-api${NC}"
    
    echo -e "\n${BLUE}=== CLI ACCESS ===${NC}"
    echo -e "CLI Panel: ${YELLOW}owpanel${NC}"
    echo -e "You can now access the CLI management panel using the 'owpanel' command from anywhere."
    
    echo -e "\n${GREEN}Installation completed successfully!${NC}"
}

# --- Main Installation Process ---

function main() {
    check_root
    
    if [ -f "/etc/systemd/system/openvpn-api.service" ] && systemctl is-enabled --quiet openvpn-api 2>/dev/null; then
        echo "System is already installed. Do you want to update the panel? (y/N): "
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_header "Updating System"
            systemctl stop openvpn-api
            cd "$PROJECT_DIR" && git reset --hard HEAD && git pull origin main
            chmod +x cli/main.py && ln -sf "$(pwd)/cli/main.py" /usr/local/bin/owpanel
            systemctl restart openvpn-api
            print_success "System updated successfully"
            exit 0
        else
            echo "Update cancelled."
            exit 0
        fi
    fi
    
    install_dependencies
    setup_project
    get_admin_credentials
    get_api_port
    setup_environment
    setup_openvpn
    setup_database
    create_api_service
    start_services
    show_completion_info
}

# Run main installation
main "$@"