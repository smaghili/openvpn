#!/bin/bash
# Enhanced deployment script for VPN Manager with JWT Authentication System
# This script sets up the complete system with enterprise-grade security

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="/etc/owpanel"
ENV_FILE="/etc/owpanel/.env"
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
    
    # Generate JWT secret
    JWT_SECRET=$(generate_jwt_secret)
    
    # Create consolidated environment file with all configurations
    cat > "$ENV_FILE" << EOF
# OpenVPN Panel Configuration
# ===========================================

# Core Path Configuration
PROJECT_ROOT=$PROJECT_DIR

# Database Paths
DATABASE_FILE=$DB_PATH
DATABASE_DIR=$PROJECT_DIR/openvpn_data

# Log File
OPENVPN_LOG_FILE=/var/log/openvpn/traffic_monitor.log

# API Configuration
API_PORT=$API_PORT
JWT_SECRET=$JWT_SECRET
API_SECRET_KEY=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
OPENVPN_API_KEY=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
FLASK_ENV=production

# Admin Configuration
ADMIN_USERNAME=$ADMIN_USERNAME

# UDS Monitor Configuration
OPENVPN_UDS_SOCKET=/run/openvpn-server/ovpn-mgmt-cert.sock
BYTECOUNT_INTERVAL=5
RECONCILE_INTERVAL=300
DB_FLUSH_INTERVAL=30
QUOTA_BUFFER_BYTES=20971520
MAX_LOG_SIZE=10485760
EOF
    
    # Set secure permissions
    chmod 600 "$ENV_FILE"
    chown root:root "$ENV_FILE"
    
    print_success "Environment configuration created"
}

function setup_database() {
    print_header "Database Setup"
    
    # Get absolute path to project directory (we're already in the project directory)
    local absolute_project_dir="$(pwd)"
    
    # Ensure database directory exists
    mkdir -p "$(dirname "$DB_PATH")"
    
    # Hash admin password
    PASSWORD_HASH=$("$absolute_project_dir/venv/bin/python3" -c "
import bcrypt
import sys
password = '$ADMIN_PASSWORD'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode('utf-8'))
")
    
    # Create database and admin user
    JWT_SECRET_VAR="$JWT_SECRET" DB_PATH_VAR="$DB_PATH" ADMIN_USERNAME_VAR="$ADMIN_USERNAME" PASSWORD_HASH_VAR="$PASSWORD_HASH" "$absolute_project_dir/venv/bin/python3" << 'EOF'
import sqlite3
import sys
import os

# Get variables from environment (passed from shell)
JWT_SECRET = os.environ.get('JWT_SECRET_VAR', '')
DB_PATH = os.environ.get('DB_PATH_VAR', '')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME_VAR', '')
PASSWORD_HASH = os.environ.get('PASSWORD_HASH_VAR', '')

print(f"Creating database at: {DB_PATH}")

# Create database connection
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Run schema creation
with open('database.sql', 'r') as f:
    schema = f.read()
    cursor.executescript(schema)

# Create admin user
print(f"Creating admin user: {ADMIN_USERNAME}")
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
    
    # Get absolute path to project directory (we're already in the project directory)
    local absolute_project_dir="$(pwd)"
    
    # Create systemd service file with absolute paths
    cat > /etc/systemd/system/openvpn-api.service << EOF
[Unit]
Description=OpenVPN Manager API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$absolute_project_dir
Environment=PATH=$absolute_project_dir/venv/bin
EnvironmentFile=$ENV_FILE
ExecStart=$absolute_project_dir/venv/bin/python -m api.app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable openvpn-api
    
    print_success "API service created and enabled"
}

function deploy_uds_monitor() {
    print_header "UDS Traffic Monitor Deployment"
    
    # Get absolute path to project directory (we're already in the project directory)
    local absolute_project_dir="$(pwd)"
    
    if [ -f "$absolute_project_dir/scripts/deploy_uds_monitor.sh" ]; then
        chmod +x "$absolute_project_dir/scripts/deploy_uds_monitor.sh"
        if PROJECT_ROOT="$absolute_project_dir" "$absolute_project_dir/scripts/deploy_uds_monitor.sh"; then
            print_success "UDS monitor deployed successfully"
        else
            print_error "UDS monitor deployment failed"
            exit 1
        fi
    else
        print_error "UDS monitor deployment script not found"
        exit 1
    fi
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
    local absolute_project_dir="$(pwd)"
    DB_PATH="$absolute_project_dir/openvpn_data/vpn_manager.db"
    
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
    
    # Set execute permissions with absolute paths
    chmod +x "$absolute_project_dir/cli/main.py" "$absolute_project_dir/api/app.py" 2>/dev/null || true
    chmod +x "$absolute_project_dir/scripts/"*.py 2>/dev/null || true
    
    print_success "Project setup completed"
}

function setup_openvpn() {
    print_header "OpenVPN Installation"
    local absolute_project_dir="$(pwd)"
    export PROJECT_ROOT="$absolute_project_dir"
    if sudo PROJECT_ROOT="$absolute_project_dir" INSTALL_ONLY=1 "$absolute_project_dir/venv/bin/python" -m cli.main; then
        print_success "OpenVPN installation completed"
    else
        print_error "OpenVPN installation failed"
        exit 1
    fi
}

function start_services() {
    print_header "Starting Services"
    
    systemctl start openvpn-api
    sleep 3
    
    if systemctl is-active --quiet openvpn-api; then
        print_success "API service started successfully"
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
    
    systemctl start openvpn-uds-monitor
    sleep 2
    
    if systemctl is-active --quiet openvpn-uds-monitor; then
        print_success "UDS monitor service started successfully"
    else
        print_warning "UDS monitor service failed to start, but continuing..."
        systemctl status openvpn-uds-monitor --no-pager
    fi
}

function show_completion_info() {
    print_header "Installation Complete"
    
    echo -e "${GREEN}🎉 OpenVPN Manager with JWT Authentication has been successfully installed!${NC}\n"
    
    echo -e "${BLUE}=== AUTHENTICATION DETAILS ===${NC}"
    echo -e "Admin Username: ${YELLOW}$ADMIN_USERNAME${NC}"
    echo -e "Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}"
    echo -e "API URL: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT${NC}"
    echo -e "Health Check: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT/api/health${NC}"
    
    echo -e "\n${BLUE}=== CLI ACCESS ===${NC}"
    echo -e "CLI Panel: ${YELLOW}owpanel${NC}"
    echo -e "You can now access the CLI management panel using the 'owpanel' command from anywhere."
    
    echo -e "\n${GREEN}Installation completed successfully!${NC}"
}

# --- Main Installation Process ---

function check_installation_status() {
    local missing_files=()
    local incomplete_installation=false
    
    # Check essential files
    [[ ! -f "/etc/systemd/system/openvpn-api.service" ]] && missing_files+=("openvpn-api.service")
    [[ ! -f "/etc/openvpn-manager/.env" ]] && missing_files+=("environment file")
    [[ ! -f "/usr/local/bin/owpanel" ]] && missing_files+=("CLI symlink")
    [[ ! -d "openvpn" ]] && missing_files+=("project directory")
    [[ ! -d "venv" ]] && missing_files+=("Python virtual environment")
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        incomplete_installation=true
    fi
    
    echo "$incomplete_installation"
}

function complete_uninstall() {
    print_header "Complete System Uninstallation"
    
    # Stop and disable services
    systemctl stop openvpn-api 2>/dev/null || true
systemctl disable openvpn-api 2>/dev/null || true
    
    # Remove systemd services
    rm -f /etc/systemd/system/openvpn-api.service
    # Removed openvpn-monitor.service - now using UDS monitor
    systemctl daemon-reload
    
    # Remove configuration files
    rm -rf /etc/openvpn-manager/
    
    # Remove project files
    cd /root 2>/dev/null || cd /home/* 2>/dev/null || cd /
    rm -rf openvpn/
    
    # Remove symlinks
    rm -f /usr/local/bin/owpanel
    
    # Remove log files
    rm -rf /var/log/openvpn/
    
    # Remove database files
    find / -name "vpn_manager.db" -delete 2>/dev/null || true
    
    print_success "Complete uninstallation finished"
}

function show_installation_menu() {
    local incomplete_installation=$(check_installation_status)
    
    print_header "Installation Menu"
    
    if [[ "$incomplete_installation" == "true" ]]; then
        echo -e "${YELLOW}⚠️  Incomplete installation detected${NC}"
        echo "Some system components are missing or corrupted."
        echo ""
    else
        echo -e "${GREEN}✅ Complete installation detected${NC}"
        echo "All system components are present."
        echo ""
    fi
    
    echo "Please select an option:"
    echo "1) Update existing installation"
    echo "2) Complete re-install (uninstall + fresh install)"
    echo "3) Exit"
    echo ""
    
    while true; do
        echo -n "Enter your choice (1-3): "
        read -r choice
        
        case $choice in
            1)
                print_header "Updating System"
                systemctl stop openvpn-api
                cd "$PROJECT_DIR" && git reset --hard HEAD && git pull origin main
                chmod +x cli/main.py && ln -sf "$(pwd)/cli/main.py" /usr/local/bin/owpanel
                systemctl restart openvpn-api
                print_success "System updated successfully"
                exit 0
                ;;
            2)
                print_header "Complete Re-installation"
                complete_uninstall
                # Continue with fresh installation
                return
                ;;
            3)
                echo "Installation cancelled."
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please enter 1, 2, or 3."
                ;;
        esac
    done
}

function main() {
    check_root
    
    if [ -f "/etc/systemd/system/openvpn-api.service" ]; then
        show_installation_menu
    fi
    
    install_dependencies
    setup_project
    get_admin_credentials
    get_api_port
    setup_environment
    setup_database
    setup_openvpn
    create_api_service
    deploy_uds_monitor
    start_services
    show_completion_info
}

# Run main installation
main "$@"