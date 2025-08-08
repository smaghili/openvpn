#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root"
    exit 1
fi

# Configuration
PROJECT_ROOT="/root/openvpn"
SERVICE_FILE="api/openvpn-api.service"
SERVICE_NAME="openvpn-api"
VENV_PATH="$PROJECT_ROOT/venv"
DEPLOY_ENV_FILE="/etc/openvpn-manager/.env"

print_info "Installing OpenVPN API systemd service..."

# Check if project directory exists
if [[ ! -d "$PROJECT_ROOT" ]]; then
    print_error "Project directory $PROJECT_ROOT not found"
    exit 1
fi

# Check if virtual environment exists
if [[ ! -d "$VENV_PATH" ]]; then
    print_error "Virtual environment not found at $VENV_PATH"
    print_info "Please run the main installation script first"
    exit 1
fi

# Check if service file exists
if [[ ! -f "$PROJECT_ROOT/$SERVICE_FILE" ]]; then
    print_error "Service file $SERVICE_FILE not found"
    exit 1
fi

# Check if environment.env exists
if [[ ! -f "$PROJECT_ROOT/environment.env" ]]; then
    print_error "Environment file $PROJECT_ROOT/environment.env not found"
    exit 1
fi

# Check if deploy environment file exists
if [[ ! -f "$DEPLOY_ENV_FILE" ]]; then
    print_error "Deploy environment file $DEPLOY_ENV_FILE not found"
    print_info "Please run deploy.sh first to configure the system"
    exit 1
fi

# Read API_PORT from deploy.sh environment file
API_PORT=$(grep "^API_PORT=" "$DEPLOY_ENV_FILE" | cut -d'=' -f2)

if [[ -z "$API_PORT" ]]; then
    print_error "API_PORT not found in $DEPLOY_ENV_FILE"
    print_info "Please run deploy.sh first to configure the system"
    exit 1
fi

print_info "Using existing configuration:"
print_info "  API_PORT: $API_PORT"
print_info "  Configuration files:"
print_info "    - $DEPLOY_ENV_FILE (deploy.sh settings)"
print_info "    - $PROJECT_ROOT/environment.env (project settings)"

# Create log directory
mkdir -p /var/log/openvpn
chmod 755 /var/log/openvpn

# Copy service file to systemd directory
cp "$PROJECT_ROOT/$SERVICE_FILE" /etc/systemd/system/

# Set proper permissions
chmod 644 /etc/systemd/system/$SERVICE_NAME.service

# Reload systemd daemon
systemctl daemon-reload

# Enable service
systemctl enable $SERVICE_NAME

print_success "Service installed and enabled"

# Check if service can start
print_info "Testing service startup..."
if systemctl start $SERVICE_NAME; then
    print_success "Service started successfully"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Service is running"
        print_info "Service status:"
        systemctl status $SERVICE_NAME --no-pager -l
    else
        print_error "Service failed to start"
        print_info "Checking logs:"
        journalctl -u $SERVICE_NAME --no-pager -l -n 20
        exit 1
    fi
else
    print_error "Failed to start service"
    print_info "Checking logs:"
    journalctl -u $SERVICE_NAME --no-pager -l -n 20
    exit 1
fi

print_info "Service management commands:"
echo "  Start:   systemctl start $SERVICE_NAME"
echo "  Stop:    systemctl stop $SERVICE_NAME"
echo "  Restart: systemctl restart $SERVICE_NAME"
echo "  Status:  systemctl status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
print_info "API will be available at:"
echo "  http://YOUR_IP:$API_PORT/api"
echo "  Health check: http://YOUR_IP:$API_PORT/api/health"
echo ""
print_info "Configuration files:"
echo "  $DEPLOY_ENV_FILE (API settings from deploy.sh)"
echo "  $PROJECT_ROOT/environment.env (project settings)"
echo ""
print_info "To change configuration:"
echo "  1. Edit $DEPLOY_ENV_FILE for API settings"
echo "  2. Edit $PROJECT_ROOT/environment.env for project settings"
echo "  3. Restart service: systemctl restart $SERVICE_NAME" 