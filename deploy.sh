#!/bin/bash

set -e
set -o pipefail

REPO_URL="https://github.com/smaghili/openvpn.git"
BRANCH="ui-version"
PROJECT_DIR="/etc/owpanel"
ENV_FILE="/etc/owpanel/.env"
DB_PATH=""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/var/log/openvpn/deploy.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function setup_logging() {
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    chown root:root "$LOG_FILE"
}

function log_info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [INFO] $message" >> "$LOG_FILE"
    echo -e "${GREEN}[INFO] $message${NC}"
}

function log_warn() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [WARN] $message" >> "$LOG_FILE"
    echo -e "${YELLOW}[WARN] $message${NC}"
}

function log_error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [ERROR] $message" >> "$LOG_FILE"
    echo -e "${RED}[ERROR] $message${NC}"
}

function check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Script must be run with root privileges"
        exit 1
    fi
}



function generate_random_credentials() {
    log_info "[2/7] Generating random credentials..."
    
    ADMIN_USERNAME="admin_$(openssl rand -hex 4)"
    ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)
    API_PORT=$(shuf -i 3000-9999 -n 1)
    
    log_info "   └── Username: $ADMIN_USERNAME"
    log_info "   └── Password: $ADMIN_PASSWORD"
    log_info "   └── API Port: $API_PORT"
}

function install_dependencies() {
    log_info "[3/7] Installing system dependencies..."
    log_info "   └── Updating package lists..."
    
    apt-get update -qq >/dev/null 2>&1
    
    log_info "   └── Installing required packages..."
    apt-get install -y -qq git python3-venv python3-pip openssl netstat-nat >/dev/null 2>&1
    
    log_info "   └── Dependencies installed successfully"
}

function setup_firewall() {
    log_info "[4/7] Configuring firewall rules..."
    log_info "   └── Detecting network interface..."
    
    local interface=$(ip route | grep default | awk '{print $5}' | head -1)
    log_info "   └── Using interface: $interface"
    
    log_info "   └── Enabling IP forwarding..."
    echo 1 > /proc/sys/net/ipv4/ip_forward
    
    log_info "   └── Configuring iptables rules..."
    iptables -t nat -A POSTROUTING -o "$interface" -j MASQUERADE 2>/dev/null || true
    
    log_info "   └── Firewall configured successfully"
}

function setup_project() {
    log_info "[5/7] Setting up project..."
    log_info "   └── Cloning repository..."
    
    if [ -d "$PROJECT_DIR" ]; then
        rm -rf "$PROJECT_DIR"
    fi
    
    git clone -q "$REPO_URL" "$PROJECT_DIR" >/dev/null 2>&1
    cd "$PROJECT_DIR"
    git checkout -q "$BRANCH" >/dev/null 2>&1
    
    log_info "   └── Creating Python virtual environment..."
    python3 -m venv venv >/dev/null 2>&1
    
    log_info "   └── Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1
    pip install -r requirements.txt >/dev/null 2>&1
    
    DB_PATH="$PROJECT_DIR/openvpn_data/vpn_manager.db"
    log_info "   └── Project setup completed"
}

function setup_environment() {
    log_info "[6/7] Configuring environment..."
    
    local public_ip=$(hostname -I | awk '{print $1}')
    local jwt_secret=$(openssl rand -base64 64 | tr -d '\n' | tr -d '=+/')
    local api_secret_key=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
    local openvpn_api_key=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
    
    mkdir -p "$(dirname "$ENV_FILE")"
    
    cat > "$ENV_FILE" << EOF
PROJECT_ROOT=$PROJECT_DIR
DATABASE_FILE=$DB_PATH
DATABASE_DIR=$PROJECT_DIR/openvpn_data
OPENVPN_LOG_FILE=/var/log/openvpn/traffic_monitor.log
API_PORT=$API_PORT
JWT_SECRET=$jwt_secret
API_SECRET_KEY=$api_secret_key
OPENVPN_API_KEY=$openvpn_api_key
FLASK_ENV=production
ADMIN_USERNAME=$ADMIN_USERNAME
OPENVPN_UDS_SOCKET=/run/openvpn-server/ovpn-mgmt-cert.sock
BYTECOUNT_INTERVAL=5
RECONCILE_INTERVAL=300
DB_FLUSH_INTERVAL=30
QUOTA_BUFFER_BYTES=20971520
MAX_LOG_SIZE=10485760
EOF
    
    chmod 600 "$ENV_FILE"
    chown root:root "$ENV_FILE"
    
    log_info "   └── Environment configured successfully"
}

function setup_database() {
    log_info "[7/7] Setting up database..."
    
    mkdir -p "$(dirname "$DB_PATH")"
    
    local password_hash=$(cd "$PROJECT_DIR" && source venv/bin/activate && python3 -c "
import bcrypt
password = '$ADMIN_PASSWORD'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode('utf-8'))
")
    
    cd "$PROJECT_DIR" && source venv/bin/activate && python3 << EOF
import sqlite3
import os

DB_PATH = '$DB_PATH'
ADMIN_USERNAME = '$ADMIN_USERNAME'
PASSWORD_HASH = '$password_hash'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

with open('database.sql', 'r') as f:
    schema = f.read()
    cursor.executescript(schema)

cursor.execute('SELECT id FROM admins WHERE username = ?', (ADMIN_USERNAME,))
row = cursor.fetchone()
if not row:
    cursor.execute(
        'INSERT INTO admins (username, password_hash, role) VALUES (?, ?, ?)',
        (ADMIN_USERNAME, PASSWORD_HASH, 'admin')
    )
    admin_id = cursor.lastrowid
    
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
        except:
            pass

conn.commit()
conn.close()
EOF
    
    chmod 644 "$DB_PATH"
    chown root:root "$DB_PATH"
    
    log_info "   └── Database setup completed"
}

function install_openvpn() {
    log_info "Installing OpenVPN with automated configuration..."
    
    local public_ip=$(hostname -I | awk '{print $1}')
    
    cd "$PROJECT_DIR" && source venv/bin/activate && python3 << EOF
import os
import sys
sys.path.append('.')

os.environ['PUBLIC_IP'] = '$public_ip'
os.environ['CERT_PORT'] = '7015'
os.environ['CERT_PROTO'] = 'udp'
os.environ['LOGIN_PORT'] = '7016'
os.environ['LOGIN_PROTO'] = 'udp'
os.environ['DNS'] = '3'
os.environ['CIPHER'] = 'AES-256-GCM'
os.environ['CERT_SIZE'] = '2048'

from cli.main import install_flow
from core.openvpn_manager import OpenVPNManager
from config.config import VPNConfig

config = VPNConfig()
openvpn_manager = OpenVPNManager(config)
install_flow(openvpn_manager)
EOF
    
    log_info "   └── OpenVPN installation completed"
}

function create_services() {
    log_info "Creating system services..."
    
    cat > /etc/systemd/system/openvpn-api.service << EOF
[Unit]
Description=OpenVPN Manager API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="UI_PATH=$PROJECT_DIR/ui"
EnvironmentFile=$ENV_FILE
ExecStart=$PROJECT_DIR/venv/bin/python -m api.app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable openvpn-api
    
    if [ -f "$PROJECT_DIR/scripts/deploy_uds_monitor.sh" ]; then
        chmod +x "$PROJECT_DIR/scripts/deploy_uds_monitor.sh"
        PROJECT_ROOT="$PROJECT_DIR" "$PROJECT_DIR/scripts/deploy_uds_monitor.sh" >/dev/null 2>&1
    fi
    
    log_info "   └── Services created successfully"
}

function start_services() {
    log_info "Starting services..."
    
    systemctl start openvpn-api
    sleep 3
    
    if systemctl is-active --quiet openvpn-api; then
        log_info "   └── API service started successfully"
    else
        log_error "   └── Failed to start API service"
        exit 1
    fi
    
    systemctl start openvpn-uds-monitor 2>/dev/null || true
    
    log_info "   └── All services started successfully"
}

function show_credentials() {
    local public_ip=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}🎉 Installation completed successfully!${NC}\n"
    echo -e "${BLUE}=== CREDENTIALS ===${NC}"
    echo -e "Admin Username: ${YELLOW}$ADMIN_USERNAME${NC}"
    echo -e "Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}"
    echo -e "API URL: ${YELLOW}http://$public_ip:$API_PORT${NC}"
    echo -e "Login Page: ${YELLOW}http://$public_ip:$API_PORT/${NC}"
    echo -e "\n${BLUE}=== CLI ACCESS ===${NC}"
    echo -e "CLI Panel: ${YELLOW}owpanel${NC}"
    echo -e "\n${GREEN}Installation completed!${NC}"
}

function create_cli_symlink() {
    log_info "Creating CLI symlink..."
    
    if [ -f "$PROJECT_DIR/cli/main.py" ]; then
        chmod +x "$PROJECT_DIR/cli/main.py"
        ln -sf "$PROJECT_DIR/cli/main.py" /usr/local/bin/owpanel
        log_info "   └── CLI symlink created successfully"
    else
        log_error "   └── CLI main.py not found"
    fi
}

function main() {
    setup_logging
    check_root
    
    log_info "Starting automated OpenVPN Manager installation..."
    
    install_dependencies
    setup_firewall
    setup_project
    generate_random_credentials
    setup_environment
    setup_database
    install_openvpn
    create_services
    create_cli_symlink
    start_services
    
    show_credentials
}

main "$@"
