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
PROJECT_ROOT="/root/openvpn"
SERVICE_NAME="openvpn-uds-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
UDS_SOCKET="/run/openvpn/ovpn-mgmt.sock"
OPENVPN_CONFIG="/etc/openvpn/server.conf"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
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
    
    # Check if UDS management is already configured
    if grep -q "management.*unix" "$OPENVPN_CONFIG" 2>/dev/null; then
        log_warn "UDS management interface already configured in OpenVPN"
        return
    fi
    

    
    # Add UDS management configuration
    echo "" >> "$OPENVPN_CONFIG"
    echo "# UDS Management Interface for Traffic Monitoring" >> "$OPENVPN_CONFIG"
    echo "management $UDS_SOCKET unix" >> "$OPENVPN_CONFIG"
    echo "status-version 3" >> "$OPENVPN_CONFIG"
    
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
    
    # Copy service file
    cp "$PROJECT_ROOT/scripts/openvpn-uds-monitor.service" "$SERVICE_FILE"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    log_info "UDS monitor service deployed and enabled"
}

setup_directories() {
    log_info "Setting up required directories..."
    
    # Create log directory
    mkdir -p /var/log/openvpn
    chmod 755 /var/log/openvpn
    
    # Create database directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/openvpn_data"
    chmod 700 "$PROJECT_ROOT/openvpn_data"
    
    log_info "Directories configured"
}

update_environment_config() {
    log_info "Updating environment configuration..."
    
    # Update environment.env with UDS-specific settings
    if [[ -f "$PROJECT_ROOT/environment.env" ]]; then
        # Add UDS configuration if not present
        if ! grep -q "OPENVPN_UDS_SOCKET" "$PROJECT_ROOT/environment.env"; then
            echo "" >> "$PROJECT_ROOT/environment.env"
            echo "# UDS Monitor Configuration" >> "$PROJECT_ROOT/environment.env"
            echo "OPENVPN_UDS_SOCKET=$UDS_SOCKET" >> "$PROJECT_ROOT/environment.env"
            echo "BYTECOUNT_INTERVAL=5" >> "$PROJECT_ROOT/environment.env"
            echo "RECONCILE_INTERVAL=300" >> "$PROJECT_ROOT/environment.env"
            echo "DB_FLUSH_INTERVAL=30" >> "$PROJECT_ROOT/environment.env"
            echo "QUOTA_BUFFER_BYTES=20971520" >> "$PROJECT_ROOT/environment.env"
        fi
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