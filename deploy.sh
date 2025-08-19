#!/bin/bash
# Enhanced deployment script for VPN Manager with JWT Authentication System
# This script sets up the complete system with enterprise-grade security

set -e # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Fail if any command in a pipeline fails

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
BRANCH="ui-version"
PROJECT_DIR="/etc/owpanel"
ENV_FILE="/etc/owpanel/.env"
# Use the same database path that the application uses (will be set dynamically)
DB_PATH=""
# Script directory (source repository)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Logging configuration
LOG_FILE="/var/log/openvpn/deploy.log"
LOG_LEVEL="INFO" # DEBUG, INFO, WARN, ERROR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Logging Functions ---

function setup_logging() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Create log file if it doesn't exist
    touch "$LOG_FILE"
    
    # Set proper permissions
    chmod 644 "$LOG_FILE"
    chown root:root "$LOG_FILE"
}

function log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Write to log file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Also output to console based on log level
    case "$level" in
        "DEBUG")
            if [ "$LOG_LEVEL" = "DEBUG" ]; then
                echo -e "${BLUE}[DEBUG] $message${NC}"
            fi
            ;;
        "INFO")
            if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
                echo -e "${GREEN}[INFO] $message${NC}"
            fi
            ;;
        "WARN")
            if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ] || [ "$LOG_LEVEL" = "WARN" ]; then
                echo -e "${YELLOW}[WARN] $message${NC}"
            fi
            ;;
        "ERROR")
            echo -e "${RED}[ERROR] $message${NC}"
            ;;
    esac
}

function log_debug() {
    log_message "DEBUG" "$1"
}

function log_info() {
    log_message "INFO" "$1"
}

function log_warn() {
    log_message "WARN" "$1"
}

function log_error() {
    log_message "ERROR" "$1"
}

# --- Functions ---

function print_header() {
    local message="$1"
    log_info "=== $message ==="
    echo -e "\n${BLUE}=== $message ===${NC}\n"
}

function print_success() {
    local message="$1"
    log_info "SUCCESS: $message"
    echo -e "${GREEN}✅ $message${NC}"
}

function print_warning() {
    local message="$1"
    log_warn "WARNING: $message"
    echo -e "${YELLOW}⚠️  $message${NC}"
}

function print_error() {
    local message="$1"
    log_error "ERROR: $message"
    echo -e "${RED}❌ $message${NC}"
}

function create_backup() {
    local backup_dir="/etc/owpanel/backups"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_name="backup_${timestamp}"
    local backup_path="${backup_dir}/${backup_name}"
    
    log_info "Starting backup creation process"
    print_header "Creating Backup"
    
    # Create backup directory
    if ! mkdir -p "${backup_path}"; then
        log_error "Failed to create backup directory: ${backup_path}"
        print_error "Failed to create backup directory: ${backup_path}"
        return 1
    fi
    log_info "Backup directory created: ${backup_path}"
    
    # Backup database
    if [ -f "${DB_PATH}" ]; then
        if cp "${DB_PATH}" "${backup_path}/vpn_manager.db"; then
            log_info "Database backed up successfully"
            print_success "Database backed up"
        else
            log_error "Failed to backup database"
            print_error "Failed to backup database"
            return 1
        fi
    else
        log_warn "Database file not found: ${DB_PATH}"
    fi
    
    # Backup certificates
    if ! mkdir -p "${backup_path}/certificates"; then
        log_error "Failed to create certificates backup directory"
        print_error "Failed to create certificates backup directory"
        return 1
    fi
    
    for cert_file in /etc/openvpn/ca.crt /etc/openvpn/ca.key /etc/openvpn/server-cert.crt /etc/openvpn/server-cert.key; do
        if [ -f "${cert_file}" ]; then
            if cp "${cert_file}" "${backup_path}/certificates/"; then
                log_info "Certificate backed up: ${cert_file}"
            else
                log_warn "Failed to backup certificate: ${cert_file}"
            fi
        else
            log_debug "Certificate file not found: ${cert_file}"
        fi
    done
    print_success "Certificates backed up"
    
    # Backup configuration
    if ! mkdir -p "${backup_path}/config"; then
        log_error "Failed to create config backup directory"
        print_error "Failed to create config backup directory"
        return 1
    fi
    
    for config_file in /etc/openvpn/server-cert.conf /etc/openvpn/server-login.conf; do
        if [ -f "${config_file}" ]; then
            if cp "${config_file}" "${backup_path}/config/"; then
                log_info "Configuration backed up: ${config_file}"
            else
                log_warn "Failed to backup configuration: ${config_file}"
            fi
        else
            log_debug "Configuration file not found: ${config_file}"
        fi
    done
    print_success "Configuration backed up"
    
    log_info "Backup creation completed successfully: ${backup_path}"
    echo "${backup_path}"
}

function rollback_deployment() {
    local backup_path="$1"
    
    log_info "Starting rollback process from backup: ${backup_path}"
    print_header "Rolling Back Deployment"
    
    if [ ! -d "${backup_path}" ]; then
        log_error "Backup directory not found: ${backup_path}"
        print_error "Backup directory not found: ${backup_path}"
        return 1
    fi
    
    # Stop services
    log_info "Stopping services for rollback"
    systemctl stop openvpn@server-cert openvpn@server-login openvpn-uds-monitor openvpn-api 2>/dev/null || {
        log_warn "Some services failed to stop during rollback"
    }
    
    # Restore database
    if [ -f "${backup_path}/vpn_manager.db" ]; then
        if cp "${backup_path}/vpn_manager.db" "${DB_PATH}"; then
            log_info "Database restored successfully"
            print_success "Database restored"
        else
            log_error "Failed to restore database"
            print_error "Failed to restore database"
            return 1
        fi
    else
        log_warn "Database backup not found in rollback"
    fi
    
    # Restore certificates
    if [ -d "${backup_path}/certificates" ]; then
        for cert_file in "${backup_path}/certificates"/*; do
            if [ -f "${cert_file}" ]; then
                if cp "${cert_file}" /etc/openvpn/ && chmod 600 "/etc/openvpn/$(basename "${cert_file}")"; then
                    log_info "Certificate restored: ${cert_file}"
                else
                    log_warn "Failed to restore certificate: ${cert_file}"
                fi
            fi
        done
        print_success "Certificates restored"
    else
        log_warn "Certificates backup directory not found"
    fi
    
    # Restore configuration
    if [ -d "${backup_path}/config" ]; then
        for config_file in "${backup_path}/config"/*; do
            if [ -f "${config_file}" ]; then
                if cp "${config_file}" /etc/openvpn/; then
                    log_info "Configuration restored: ${config_file}"
                else
                    log_warn "Failed to restore configuration: ${config_file}"
                fi
            fi
        done
        print_success "Configuration restored"
    else
        log_warn "Configuration backup directory not found"
    fi
    
    # Restart services
    log_info "Restarting services after rollback"
    if ! systemctl daemon-reload; then
        log_error "Failed to reload systemd daemon"
        print_error "Failed to reload systemd daemon"
        return 1
    fi
    
    if ! systemctl start openvpn@server-cert openvpn@server-login openvpn-uds-monitor openvpn-api; then
        log_error "Failed to restart services after rollback"
        print_error "Failed to restart services after rollback"
        return 1
    fi
    
    log_info "Rollback completed successfully"
    print_success "Rollback completed successfully"
}

function check_root() {
    log_info "Checking root privileges"
    if [ "$EUID" -ne 0 ]; then
        log_error "Script must be run with root privileges"
        print_error "This script must be run with root privileges. Please use 'sudo'."
        exit 1
    fi
    log_info "Root privileges confirmed"
}

function validate_input() {
    local input="$1"
    local pattern="$2"
    local error_msg="$3"
    
    log_debug "Validating input: $input with pattern: $pattern"
    if [[ ! $input =~ $pattern ]]; then
        log_error "Input validation failed: $error_msg"
        print_error "$error_msg"
        return 1
    fi
    log_debug "Input validation passed"
    return 0
}

function check_port_available() {
    local port="$1"
    log_debug "Checking if port $port is available"
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        log_error "Port $port is already in use"
        print_error "Port $port is already in use."
        return 1
    fi
    log_debug "Port $port is available"
    return 0
}

function generate_secure_password() {
    log_info "Generating secure password"
    local password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-16)
    if [ $? -eq 0 ]; then
        log_info "Secure password generated successfully"
        echo "$password"
    else
        log_error "Failed to generate secure password"
        print_error "Failed to generate secure password"
        exit 1
    fi
}

function generate_jwt_secret() {
    log_info "Generating JWT secret"
    local secret=$(openssl rand -base64 64 | tr -d '\n' | tr -d '=+/')
    if [ $? -eq 0 ]; then
        log_info "JWT secret generated successfully"
        echo "$secret"
    else
        log_error "Failed to generate JWT secret"
        print_error "Failed to generate JWT secret"
        exit 1
    fi
}

function get_admin_credentials() {
    log_info "Starting admin credentials setup"
    print_header "Admin Account Setup"
    
    # Get admin username with validation
    while true; do
        echo -n "Enter admin username (3-50 chars, default: admin): "
        read ADMIN_USERNAME
        ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
        log_info "Admin username entered: $ADMIN_USERNAME"
        
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
            log_info "Auto-generated admin password"
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
                log_info "Admin password confirmed successfully"
                break
            else
                log_error "Password confirmation failed"
                print_error "Passwords do not match."
            fi
        else
            log_error "Password too short: ${#ADMIN_PASSWORD} characters"
            print_error "Password must be at least 8 characters."
        fi
    done
}

function get_api_port() {
    log_info "Starting API port configuration"
    print_header "API Server Configuration"
    
    while true; do
        echo -n "Enter API port (1024-65535, default: random): "
        read API_PORT
        
        if [ -z "$API_PORT" ]; then
            API_PORT=$(shuf -i 3000-9999 -n 1)
            log_info "Auto-generated API port: $API_PORT"
            print_success "Generated port: $API_PORT"
            break
        elif validate_input "$API_PORT" "^[0-9]+$" "Port must be numeric." && 
             [ "$API_PORT" -ge 1024 ] && [ "$API_PORT" -le 65535 ]; then
            if check_port_available "$API_PORT"; then
                log_info "API port configured: $API_PORT"
                break
            fi
        else
            log_error "Invalid API port: $API_PORT"
            print_error "Invalid port. Must be between 1024-65535."
        fi
    done
}

function setup_environment() {
    log_info "Starting environment configuration"
    print_header "Environment Configuration"
    
    # Generate JWT secret
    JWT_SECRET=$(generate_jwt_secret)
    if [ $? -ne 0 ]; then
        log_error "Failed to generate JWT secret"
        print_error "Failed to generate JWT secret"
        return 1
    fi
    
    # Create consolidated environment file with all configurations
    log_info "Creating environment file: $ENV_FILE"
    
    # Generate API secret key
    local api_secret_key=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
    if [ $? -ne 0 ]; then
        log_error "Failed to generate API secret key"
        print_error "Failed to generate API secret key"
        return 1
    fi
    
    # Generate OpenVPN API key
    local openvpn_api_key=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
    if [ $? -ne 0 ]; then
        log_error "Failed to generate OpenVPN API key"
        print_error "Failed to generate OpenVPN API key"
        return 1
    fi
    
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
API_SECRET_KEY=$api_secret_key
OPENVPN_API_KEY=$openvpn_api_key
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
    
    if [ $? -ne 0 ]; then
        log_error "Failed to create environment file"
        print_error "Failed to create environment file"
        return 1
    fi
    
    if ! chmod 600 "$ENV_FILE"; then
        log_error "Failed to set permissions on environment file"
        print_error "Failed to set permissions on environment file"
        return 1
    fi
    
    if ! chown root:root "$ENV_FILE"; then
        log_error "Failed to set ownership on environment file"
        print_error "Failed to set ownership on environment file"
        return 1
    fi
    
    log_info "Environment configuration completed successfully"
    print_success "Environment configuration created"
}

function setup_database() {
    log_info "Starting database setup"
    print_header "Database Setup"
    
    try {
        # Get absolute path to project directory (we're already in the project directory)
        local absolute_project_dir="$(pwd)"
        log_info "Project directory: $absolute_project_dir"
        
        # Ensure database directory exists
        mkdir -p "$(dirname "$DB_PATH")"
        log_info "Database directory created: $(dirname "$DB_PATH")"
        
        # Hash admin password
        log_info "Hashing admin password"
        PASSWORD_HASH=$("$absolute_project_dir/venv/bin/python3" -c "
import bcrypt
import sys
password = '$ADMIN_PASSWORD'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
echo "Password hash generated"
")
        
        # Create database and admin user
        log_info "Creating database and admin user"
        JWT_SECRET_VAR="$JWT_SECRET" DB_PATH_VAR="$DB_PATH" ADMIN_USERNAME_VAR="$ADMIN_USERNAME" PASSWORD_HASH_VAR="$PASSWORD_HASH" "$absolute_project_dir/venv/bin/python3" << 'EOF'
import sqlite3
import sys
import os

# Get variables from environment (passed from shell)
JWT_SECRET = os.environ.get('JWT_SECRET_VAR', '')
DB_PATH = os.environ.get('DB_PATH_VAR', '')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME_VAR', '')
PASSWORD_HASH = os.environ.get('PASSWORD_HASH_VAR', '')

echo "Creating database"

# Create database connection
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Run schema creation
with open('database.sql', 'r') as f:
    schema = f.read()
    cursor.executescript(schema)

# Create admin user if it doesn't already exist
print(f"Creating admin user: {ADMIN_USERNAME}")
cursor.execute('SELECT id FROM admins WHERE username = ?', (ADMIN_USERNAME,))
row = cursor.fetchone()
if row:
    admin_id = row[0]
    print(f"Admin user {ADMIN_USERNAME} already exists with ID: {admin_id}")
else:
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
        
        log_info "Database setup completed successfully"
        print_success "Database setup completed"
    } catch {
        log_error "Database setup failed: $1"
        print_error "Database setup failed: $1"
        return 1
    }
}

function create_api_service() {
    log_info "Starting API service setup"
    print_header "API Service Setup"
    
    try {
        # Get absolute path to project directory (we're already in the project directory)
        local absolute_project_dir="$(pwd)"
        log_info "Creating API service for project directory: $absolute_project_dir"
        
        # Create systemd service file with absolute paths
        cat > /etc/systemd/system/openvpn-api.service << EOF
[Unit]
Description=OpenVPN Manager API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$absolute_project_dir
Environment="PATH=$absolute_project_dir/venv/bin"
Environment="UI_PATH=$absolute_project_dir/ui"
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
        
        log_info "API service created and enabled successfully"
        print_success "API service created and enabled"
    } catch {
        log_error "API service creation failed: $1"
        print_error "API service creation failed: $1"
        return 1
    }
}

function deploy_systemd_optimization() {
    log_info "Starting systemd optimization deployment"
    print_header "OpenVPN Service Optimization"
    
    try {
        # Create systemd override directory
        mkdir -p /etc/systemd/system/openvpn@server-login.service.d/
        log_info "Created systemd override directory"
        
        # Copy systemd override configuration if it exists in project
        local absolute_project_dir="$(pwd)"
        if [ -f "$absolute_project_dir/systemd/system/openvpn@server-login.service.d/override.conf" ]; then
            cp "$absolute_project_dir/systemd/system/openvpn@server-login.service.d/override.conf" \
               /etc/systemd/system/openvpn@server-login.service.d/
            log_info "Applied existing systemd optimization configuration"
            print_success "OpenVPN service optimization applied"
        else
            # Create default optimization configuration
            log_info "Creating default systemd optimization configuration"
            cat > /etc/systemd/system/openvpn@server-login.service.d/override.conf << 'EOF'
[Service]
# Professional timeout configuration for PAM-based authentication
TimeoutStopSec=10s
TimeoutStartSec=10s

# Enhanced kill behavior for problematic PAM plugin
KillMode=mixed
KillSignal=SIGTERM

# Restart policy optimization
Restart=on-failure
RestartSec=3s

# Resource limits for stability
LimitNOFILE=65536
LimitNPROC=32768

# Security enhancements
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true

# Performance tuning
Nice=-5
EOF
            log_info "Default systemd optimization configuration created"
            print_success "Default OpenVPN service optimization created"
        fi
        
        # Reload systemd configuration
        systemctl daemon-reload
        log_info "systemd configuration reloaded successfully"
        print_success "systemd configuration reloaded"
    } catch {
        log_error "Systemd optimization deployment failed: $1"
        print_error "Systemd optimization deployment failed: $1"
        return 1
    }
}

function deploy_uds_monitor() {
    log_info "Starting UDS monitor deployment"
    print_header "UDS Traffic Monitor Deployment"
    
    try {
        # Get absolute path to project directory (we're already in the project directory)
        local absolute_project_dir="$(pwd)"
        log_info "Deploying UDS monitor from project directory: $absolute_project_dir"
        
        if [ -f "$absolute_project_dir/scripts/deploy_uds_monitor.sh" ]; then
            chmod +x "$absolute_project_dir/scripts/deploy_uds_monitor.sh"
            if PROJECT_ROOT="$absolute_project_dir" "$absolute_project_dir/scripts/deploy_uds_monitor.sh"; then
                log_info "UDS monitor deployed successfully"
                print_success "UDS monitor deployed successfully"
            else
                log_error "UDS monitor deployment failed"
                print_error "UDS monitor deployment failed"
                exit 1
            fi
        else
            log_error "UDS monitor deployment script not found: $absolute_project_dir/scripts/deploy_uds_monitor.sh"
            print_error "UDS monitor deployment script not found"
            exit 1
        fi
    } catch {
        log_error "UDS monitor deployment failed: $1"
        print_error "UDS monitor deployment failed: $1"
        return 1
    }
}

function install_dependencies() {
    log_info "Starting dependency installation"
    print_header "Installing Dependencies"
    
    try {
        log_info "Updating package lists"
        echo "Installing system packages..."
        apt-get update
        log_info "Installing required system packages"
        apt-get install -y git python3-venv python3-pip openssl netstat-nat
        
        log_info "System packages installed successfully"
        print_success "System packages installed"
    } catch {
        log_error "Dependency installation failed: $1"
        print_error "Dependency installation failed: $1"
        return 1
    }
}

function setup_project() {
    log_info "Starting project setup"
    print_header "Project Setup"
    
    try {
        if [ -d "$PROJECT_DIR" ]; then
            log_info "Project directory exists, updating repository"
            echo "Project directory exists. Fetching latest version..."
            cd "$PROJECT_DIR"
            
            # Check if this is a git repository
            if [ -d ".git" ]; then
                log_info "Cleaning up local changes"
                echo "Cleaning up any local changes..."
                git reset --hard HEAD || {
                    log_error "Failed to reset git repository"
                    print_error "Failed to reset git repository"
                    exit 1
                }
                git clean -fd || {
                    log_warn "Failed to clean git repository, continuing..."
                }
                
                # Check current branch and handle conflicts
                current_branch=$(git branch --show-current 2>/dev/null || echo "main")
                log_info "Current branch: $current_branch"
                echo "Current branch: $current_branch"
                
                # Fetch latest changes
                log_info "Fetching latest changes from remote"
                echo "Fetching latest changes from remote..."
                git fetch origin || {
                    log_error "Failed to fetch from remote repository"
                    print_error "Failed to fetch from remote repository"
                    exit 1
                }
                
                # Check if we can fast-forward or need to reset
                if git merge-base --is-ancestor HEAD origin/ui-version 2>/dev/null; then
                    log_info "Performing fast-forward merge"
                    echo "Fast-forward merge possible"
                    git pull origin ui-version || {
                        log_error "Failed to pull from ui-version branch"
                        print_error "Failed to pull from ui-version branch"
                        exit 1
                    }
                else
                    log_info "Divergent branches detected, resetting to origin/ui-version"
                    echo "Divergent branches detected, resetting to origin/ui-version"
                    git reset --hard origin/ui-version || {
                        log_error "Failed to reset to origin/ui-version"
                        print_error "Failed to reset to origin/ui-version"
                        exit 1
                    }
                fi
                
                log_info "Repository updated successfully"
                echo "Successfully updated repository"
            else
                log_info "Directory exists but not a git repository, cloning fresh"
                echo "Directory exists but not a git repository. Removing and cloning fresh..."
                cd ..
                rm -rf "$PROJECT_DIR"
                git clone "$REPO_URL" "$PROJECT_DIR" || {
                    log_error "Failed to clone repository"
                    print_error "Failed to clone repository"
                    exit 1
                }
                cd "$PROJECT_DIR"
                git checkout ui-version || {
                    log_error "Failed to checkout ui-version branch"
                    print_error "Failed to checkout ui-version branch"
                    exit 1
                }
            fi
        else
            log_info "Cloning project repository"
            echo "Cloning project repository..."
            git clone "$REPO_URL" "$PROJECT_DIR" || {
                log_error "Failed to clone repository"
                print_error "Failed to clone repository"
                exit 1
            }
            cd "$PROJECT_DIR"
            git checkout ui-version || {
                log_error "Failed to checkout ui-version branch"
                print_error "Failed to checkout ui-version branch"
                exit 1
            }
        fi
        
        local absolute_project_dir="$(pwd)"
        DB_PATH="$absolute_project_dir/openvpn_data/vpn_manager.db"
        log_info "Database path set to: $DB_PATH"

        # Copy web UI assets into the project directory if missing
        if [ -d "$SCRIPT_DIR/ui" ] && [ ! -d "$absolute_project_dir/ui" ]; then
            log_info "Copying web UI assets"
            cp -r "$SCRIPT_DIR/ui" "$absolute_project_dir/"
        fi
        
        # Validate that essential files exist
        log_info "Validating repository contents"
        echo "Validating repository contents..."
        if [ ! -f "requirements.txt" ]; then
            log_error "requirements.txt not found in repository"
            print_error "requirements.txt not found in repository"
            exit 1
        fi
        
        if [ ! -d "cli" ] || [ ! -d "api" ]; then
            log_error "Essential directories (cli, api) not found in repository"
            print_error "Essential directories (cli, api) not found in repository"
            exit 1
        fi
        
        log_info "Setting up Python environment"
        echo "Setting up Python environment..."
        if [ ! -d "venv" ]; then
            python3 -m venv venv || {
                log_error "Failed to create Python virtual environment"
                print_error "Failed to create Python virtual environment"
                exit 1
            }
        fi
        
        source venv/bin/activate
        log_info "Upgrading pip"
        pip install --upgrade pip || {
            log_error "Failed to upgrade pip"
            print_error "Failed to upgrade pip"
            exit 1
        }
        
        if [ -f "requirements.txt" ]; then
            log_info "Installing Python dependencies from requirements.txt"
            pip install -r requirements.txt || {
                log_error "Failed to install Python dependencies"
                print_error "Failed to install Python dependencies"
                exit 1
            }
        else
            log_error "requirements.txt not found"
            print_error "requirements.txt not found"
            exit 1
        fi
        
        # Set execute permissions with absolute paths
        log_info "Setting execute permissions on Python scripts"
        chmod +x "$absolute_project_dir/cli/main.py" "$absolute_project_dir/api/app.py" 2>/dev/null || true
        chmod +x "$absolute_project_dir/scripts/"*.py 2>/dev/null || true
        
        log_info "Project setup completed successfully"
        print_success "Project setup completed"
    } catch {
        log_error "Project setup failed: $1"
        print_error "Project setup failed: $1"
        return 1
    }
}

function setup_openvpn() {
    log_info "Starting OpenVPN installation"
    print_header "OpenVPN Installation"
    
    try {
        local absolute_project_dir="$(pwd)"
        export PROJECT_ROOT="$absolute_project_dir"
        log_info "Running OpenVPN installation with PROJECT_ROOT: $absolute_project_dir"
        
        if sudo PROJECT_ROOT="$absolute_project_dir" INSTALL_ONLY=1 "$absolute_project_dir/venv/bin/python" -m cli.main; then
            log_info "OpenVPN installation completed successfully"
            print_success "OpenVPN installation completed"
        else
            log_error "OpenVPN installation failed"
            print_error "OpenVPN installation failed"
            exit 1
        fi
    } catch {
        log_error "OpenVPN setup failed: $1"
        print_error "OpenVPN setup failed: $1"
        return 1
    }
}

function start_services() {
    log_info "Starting services"
    print_header "Starting Services"
    
    try {
        # Start API service
        log_info "Starting API service"
        systemctl start openvpn-api
        sleep 3
        
        if systemctl is-active --quiet openvpn-api; then
            log_info "API service started successfully"
            print_success "API service started successfully"
            sleep 2
            
            log_info "Performing API health check"
            if curl -f http://localhost:$API_PORT/api/health >/dev/null 2>&1; then
                log_info "API health check passed"
                print_success "API health check passed"
            else
                log_warn "API health check failed, but service is running"
                print_warning "API health check failed, but service is running"
            fi
            
            log_info "Checking web panel accessibility"
            if curl -f http://localhost:$API_PORT/ | grep -qi '<!doctype html'; then
                log_info "Web panel is reachable"
                print_success "Web panel reachable"
            else
                log_warn "Web panel not reachable"
                print_warning "Web panel not reachable"
            fi
        else
            log_error "Failed to start API service"
            print_error "Failed to start API service"
            systemctl status openvpn-api
            journalctl -u openvpn-api --no-pager -n 20
            exit 1
        fi
        
        # Start UDS monitor service
        log_info "Starting UDS monitor service"
        systemctl start openvpn-uds-monitor
        sleep 2
        
        if systemctl is-active --quiet openvpn-uds-monitor; then
            log_info "UDS monitor service started successfully"
            print_success "UDS monitor service started successfully"
        else
            log_warn "UDS monitor service failed to start, but continuing..."
            print_warning "UDS monitor service failed to start, but continuing..."
            systemctl status openvpn-uds-monitor --no-pager
        fi
    } catch {
        log_error "Service startup failed: $1"
        print_error "Service startup failed: $1"
        return 1
    }
}

function show_completion_info() {
    log_info "Installation completed successfully, showing completion info"
    print_header "Installation Complete"
    
    echo -e "${GREEN}🎉 OpenVPN Manager with JWT Authentication has been successfully installed!${NC}\n"
    
    echo -e "${BLUE}=== AUTHENTICATION DETAILS ===${NC}"
    echo -e "Admin Username: ${YELLOW}$ADMIN_USERNAME${NC}"
    echo -e "Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}"
    echo -e "API URL: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT${NC}"
    echo -e "Health Check: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT/api/health${NC}"
    echo -e "Login Page: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$API_PORT/${NC}"
    echo -e "${YELLOW}Remember to change the default admin password after first login.${NC}"
    
    echo -e "\n${BLUE}=== CLI ACCESS ===${NC}"
    echo -e "CLI Panel: ${YELLOW}owpanel${NC}"
    echo -e "You can now access the CLI management panel using the 'owpanel' command from anywhere."
    
    echo -e "\n${GREEN}Installation completed successfully!${NC}"
    
    log_info "Installation completion info displayed"
}

# --- Main Installation Process ---

function check_installation_status() {
    log_info "Checking installation status"
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
        log_warn "Incomplete installation detected. Missing files: ${missing_files[*]}"
    else
        log_info "Complete installation detected"
    fi
    
    echo "$incomplete_installation"
}

function complete_uninstall() {
    log_info "Starting complete system uninstallation"
    print_header "Complete System Uninstallation"
    
    try {
        # Stop and disable services
        log_info "Stopping and disabling services"
        systemctl stop openvpn-api 2>/dev/null || true
        systemctl disable openvpn-api 2>/dev/null || true
        
        # Remove systemd services
        log_info "Removing systemd services"
        rm -f /etc/systemd/system/openvpn-api.service
        # Removed openvpn-monitor.service - now using UDS monitor
        systemctl daemon-reload
        
        # Remove configuration files
        log_info "Removing configuration files"
        rm -rf /etc/openvpn-manager/
        
        # Remove project files
        log_info "Removing project files"
        cd /root 2>/dev/null || cd /home/* 2>/dev/null || cd /
        rm -rf openvpn/
        
        # Remove symlinks
        log_info "Removing symlinks"
        rm -f /usr/local/bin/owpanel
        
        # Remove log files
        log_info "Removing log files"
        rm -rf /var/log/openvpn/
        
        # Remove database files
        log_info "Removing database files"
        find / -name "vpn_manager.db" -delete 2>/dev/null || true
        
        log_info "Complete uninstallation finished successfully"
        print_success "Complete uninstallation finished"
    } catch {
        log_error "Complete uninstall failed: $1"
        print_error "Complete uninstall failed: $1"
        return 1
    }
}

function show_installation_menu() {
    local incomplete_installation=$(check_installation_status)
    
    log_info "Showing installation menu"
    print_header "Installation Menu"
    
    if [[ "$incomplete_installation" == "true" ]]; then
        log_warn "Incomplete installation detected in menu"
        echo -e "${YELLOW}⚠️  Incomplete installation detected${NC}"
        echo "Some system components are missing or corrupted."
        echo ""
    else
        log_info "Complete installation detected in menu"
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
                log_info "User selected option 1: Update existing installation"
                print_header "Updating System"
                systemctl stop openvpn-api
                cd "$PROJECT_DIR" && git reset --hard HEAD && git pull origin ui-version
                chmod +x cli/main.py && ln -sf "$(pwd)/cli/main.py" /usr/local/bin/owpanel
                systemctl restart openvpn-api
                log_info "System updated successfully"
                print_success "System updated successfully"
                exit 0
                ;;
            2)
                log_info "User selected option 2: Complete re-installation"
                print_header "Complete Re-installation"
                complete_uninstall
                # Continue with fresh installation
                return
                ;;
            3)
                log_info "User selected option 3: Exit installation"
                echo "Installation cancelled."
                exit 0
                ;;
            *)
                log_error "Invalid menu choice: $choice"
                print_error "Invalid choice. Please enter 1, 2, or 3."
                ;;
        esac
    done
}

function cleanup_old_backups() {
    log_info "Starting cleanup of old backups"
    local backup_dir="/etc/owpanel/backups"
    local keep_count=5
    
    try {
        if [ -d "${backup_dir}" ]; then
            cd "${backup_dir}"
            ls -t | tail -n +$((keep_count + 1)) | xargs -r rm -rf
            log_info "Old backups cleaned up successfully"
            print_success "Old backups cleaned up"
        else
            log_info "Backup directory not found, skipping cleanup"
        fi
    } catch {
        log_error "Backup cleanup failed: $1"
        print_error "Backup cleanup failed: $1"
    }
}

function main() {
    log_info "Starting main installation process"
    
    # Setup logging first
    setup_logging
    log_info "Logging system initialized"
    
    check_root
    
    if [ -f "/etc/systemd/system/openvpn-api.service" ]; then
        log_info "Existing installation detected, showing menu"
        show_installation_menu
    fi
    
    # Create backup before deployment
    log_info "Creating backup before deployment"
    BACKUP_PATH=$(create_backup)
    
    # Get database path
    log_info "Getting database path"
    DB_PATH=$(python3 -c "from config.config import config; print(config.DATABASE_FILE)" 2>/dev/null || echo "/etc/owpanel/vpn_manager.db")
    log_info "Database path: $DB_PATH"
    
    # Install dependencies
    log_info "Installing dependencies"
    if ! install_dependencies; then
        log_error "Dependency installation failed, rolling back"
        print_error "Dependency installation failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Setup project
    log_info "Setting up project"
    if ! setup_project; then
        log_error "Project setup failed, rolling back"
        print_error "Project setup failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Get admin credentials
    log_info "Getting admin credentials"
    get_admin_credentials
    
    # Get API port
    log_info "Getting API port"
    get_api_port
    
    # Setup environment
    log_info "Setting up environment"
    if ! setup_environment; then
        log_error "Environment setup failed, rolling back"
        print_error "Environment setup failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Setup database
    log_info "Setting up database"
    if ! setup_database; then
        log_error "Database setup failed, rolling back"
        print_error "Database setup failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Setup OpenVPN
    log_info "Setting up OpenVPN"
    if ! setup_openvpn; then
        log_error "OpenVPN setup failed, rolling back"
        print_error "OpenVPN setup failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Create API service
    log_info "Creating API service"
    if ! create_api_service; then
        log_error "API service creation failed, rolling back"
        print_error "API service creation failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Deploy systemd optimization
    log_info "Deploying systemd optimization"
    deploy_systemd_optimization
    
    # Deploy UDS monitor
    log_info "Deploying UDS monitor"
    if ! deploy_uds_monitor; then
        log_error "UDS monitor deployment failed, rolling back"
        print_error "UDS monitor deployment failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Start services
    log_info "Starting services"
    if ! start_services; then
        log_error "Service startup failed, rolling back"
        print_error "Service startup failed. Rolling back..."
        rollback_deployment "${BACKUP_PATH}"
        exit 1
    fi
    
    # Cleanup old backups (keep last 5)
    log_info "Cleaning up old backups"
    cleanup_old_backups
    
    log_info "Installation completed successfully"
    show_completion_info
}

# Run main installation
main "$@"
