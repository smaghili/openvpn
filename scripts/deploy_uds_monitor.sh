#!/bin/bash

# OpenVPN UDS Traffic Monitor Deployment Script
# This script deploys the UDS-based traffic monitoring system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="${PROJECT_ROOT:-/etc/owpanel}"
UDS_SOCKET="/run/openvpn-server/ovpn-mgmt-cert.sock"
SERVICE_NAME="openvpn-uds-monitor"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
OPENVPN_CONFIG="/etc/openvpn/server.conf"

log_info() {
    if [[ "$1" == *"Starting UDS-based"* ]] || \
       [[ "$1" == *"Deployment completed"* ]] || \
       [[ "$1" == *"started successfully"* ]] || \
       [[ "$1" == *"test successful"* ]]; then
        echo -e "${GREEN}✅${NC} $1"
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_openvpn_installed() {
    if ! command -v openvpn &> /dev/null; then
        log_error "OpenVPN is not installed. Please install OpenVPN first."
        exit 1
    fi
}

backup_openvpn_config() {
    if [[ -f "$OPENVPN_CONFIG" ]]; then
        log_info "Backing up OpenVPN configuration..."
        cp "$OPENVPN_CONFIG" "${OPENVPN_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
}



configure_openvpn_uds() {
    log_info "Configuring OpenVPN for UDS management interface..."
    
    # Create /run/openvpn-server directory if it doesn't exist
    mkdir -p /run/openvpn-server
    chmod 755 /run/openvpn-server
    
    # Configure server-cert.conf
    if [[ -f "/etc/openvpn/server/server-cert.conf" ]]; then
        # Remove any existing management lines
        sed -i '/^management/d' "/etc/openvpn/server/server-cert.conf"
        
        # Add UDS management interface
        echo "" >> "/etc/openvpn/server/server-cert.conf"
        echo "# UDS Management Interface" >> "/etc/openvpn/server/server-cert.conf"
        echo "management /run/openvpn-server/ovpn-mgmt-cert.sock unix" >> "/etc/openvpn/server/server-cert.conf"
    fi
    
    # Configure server-login.conf
    if [[ -f "/etc/openvpn/server/server-login.conf" ]]; then
        # Remove any existing management lines
        sed -i '/^management/d' "/etc/openvpn/server/server-login.conf"
        
        # Add UDS management interface
        echo "" >> "/etc/openvpn/server/server-login.conf"
        echo "# UDS Management Interface" >> "/etc/openvpn/server/server-login.conf"
        echo "management /run/openvpn-server/ovpn-mgmt-login.sock unix" >> "/etc/openvpn/server/server-login.conf"
    fi
    
    log_info "Added UDS management interface configuration"
}

create_systemd_override() {
    log_info "Creating systemd override for OpenVPN service..."
    
    # Create override directory
    mkdir -p /etc/systemd/system/openvpn-server@server.service.d/
    
    # Create override file
    cat > /etc/systemd/system/openvpn-server@server.service.d/uds-override.conf << EOF
[Service]
RuntimeDirectory=openvpn
UMask=007
ExecStartPost=/usr/bin/chmod 770 /run/openvpn/ovpn-mgmt.sock
ExecStartPost=/usr/bin/chgrp openvpn /run/openvpn/ovpn-mgmt.sock
EOF
    
    log_info "Created systemd override for OpenVPN service"
}

setup_monitor_user() {
    log_info "Setting up monitor user permissions..."
    
    # Create openvpn group if it doesn't exist
    if ! getent group openvpn > /dev/null 2>&1; then
        groupadd openvpn
        log_info "Created openvpn group"
    fi
    
    # Add root user to openvpn group (since service runs as root)
    usermod -aG openvpn root 2>/dev/null || true
    
    log_info "Monitor user permissions configured"
}

deploy_service() {
    log_info "Deploying UDS monitor service..."
    
    # Create systemd service file
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=OpenVPN UDS Traffic Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/scripts/uds_monitor_service.py
Restart=always
RestartSec=10

# Environment configuration
EnvironmentFile=/etc/owpanel/.env
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    # Enable and start service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_info "UDS monitor service deployed and enabled"
}

setup_directories() {
    log_info "Setting up required directories..."
    
    # Create log directory and log file
    mkdir -p /var/log/openvpn
    chmod 755 /var/log/openvpn
    touch /var/log/openvpn/traffic_monitor.log
    chmod 644 /var/log/openvpn/traffic_monitor.log
    chown root:root /var/log/openvpn/traffic_monitor.log
    
    # Create OpenVPN server directory
    mkdir -p /run/openvpn-server
    chmod 755 /run/openvpn-server
    
    # Create database directory
    mkdir -p "$PROJECT_ROOT/openvpn_data"
    chmod 700 "$PROJECT_ROOT/openvpn_data"
    
    log_info "Directories configured"
}

update_environment_config() {
    log_info "Updating environment configuration..."
    
    # Update environment file with UDS configuration
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        # Remove existing UDS configuration if present
        sed -i '/^OPENVPN_UDS_SOCKET=/d' "$PROJECT_ROOT/.env"
        sed -i '/^BYTECOUNT_INTERVAL=/d' "$PROJECT_ROOT/.env"
        sed -i '/^RECONCILE_INTERVAL=/d' "$PROJECT_ROOT/.env"
        sed -i '/^DB_FLUSH_INTERVAL=/d' "$PROJECT_ROOT/.env"
        sed -i '/^QUOTA_BUFFER_BYTES=/d' "$PROJECT_ROOT/.env"
        
        # Add new UDS configuration
        echo "" >> "$PROJECT_ROOT/.env"
        echo "# UDS Monitor Configuration" >> "$PROJECT_ROOT/.env"
        echo "OPENVPN_UDS_SOCKET=$UDS_SOCKET" >> "$PROJECT_ROOT/.env"
        echo "BYTECOUNT_INTERVAL=5" >> "$PROJECT_ROOT/.env"
        echo "RECONCILE_INTERVAL=300" >> "$PROJECT_ROOT/.env"
        echo "DB_FLUSH_INTERVAL=30" >> "$PROJECT_ROOT/.env"
        echo "QUOTA_BUFFER_BYTES=20971520" >> "$PROJECT_ROOT/.env"
    fi
    
    log_info "Environment configuration updated"
}

test_uds_connection() {
    log_info "Testing UDS connection..."
    
    # Wait for OpenVPN to start and create socket
    sleep 5
    
    if [[ -S "$UDS_SOCKET" ]]; then
        log_info "UDS socket created successfully"
        
        # Test basic connection
        if timeout 10 bash -c "echo 'status' | socat - UNIX-CONNECT:$UDS_SOCKET" > /dev/null 2>&1; then
            log_info "UDS connection test successful"
        else
            log_warn "UDS connection test failed - this is normal if OpenVPN is not running"
        fi
    else
        log_warn "UDS socket not found - this is normal if OpenVPN is not running"
    fi
}

start_services() {
    log_info "Starting services..."
    
    # Restart OpenVPN to apply UDS configuration
    if systemctl is-active --quiet openvpn-server@server; then
        log_info "Restarting OpenVPN service to apply UDS configuration..."
        systemctl restart openvpn-server@server
        sleep 5
    fi
    
    # Start UDS monitor service
    log_info "Starting UDS monitor service..."
    systemctl start "$SERVICE_NAME"
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "UDS monitor service started successfully"
    else
        log_error "Failed to start UDS monitor service"
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

show_status() {
    log_info "Deployment completed successfully!"
    echo
    echo "=== Service Status ==="
    systemctl status "$SERVICE_NAME" --no-pager
    echo
    echo "=== Configuration Summary ==="
    echo "UDS Socket: $UDS_SOCKET"
    echo "Service File: $SERVICE_FILE"
    echo "Log File: /var/log/openvpn/traffic_monitor.log"
    echo "Database: $PROJECT_ROOT/openvpn_data/vpn_manager.db"
    echo
    echo "=== Useful Commands ==="
    echo "View logs: journalctl -u $SERVICE_NAME -f"
    echo "Check status: systemctl status $SERVICE_NAME"
    echo "Restart service: systemctl restart $SERVICE_NAME"
    echo "Stop service: systemctl stop $SERVICE_NAME"
    echo
    echo "=== Next Steps ==="
    echo "1. Set user quotas using: python3 $PROJECT_ROOT/cli/main.py"
    echo "2. Monitor traffic logs: tail -f /var/log/openvpn/traffic_monitor.log"
    echo "3. Check database: sqlite3 $PROJECT_ROOT/openvpn_data/vpn_manager.db"
}

main() {
    log_info "Starting UDS-based OpenVPN traffic monitor deployment..."
    
    check_root
    check_openvpn_installed
    backup_openvpn_config
    configure_openvpn_uds
    create_systemd_override
    setup_monitor_user
    setup_directories
    update_environment_config
    deploy_service
    test_uds_connection
    start_services
    show_status
}

# Run main function
main "$@" 