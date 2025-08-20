#!/bin/bash

# OpenVPN API Token Regeneration Script

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

DEPLOY_ENV_FILE="/etc/openvpn-manager/.env"
SERVICE_NAME="openvpn-api"

print_info "Regenerating OpenVPN API security tokens..."

# Check if deploy environment file exists
if [[ ! -f "$DEPLOY_ENV_FILE" ]]; then
    print_error "Deploy environment file $DEPLOY_ENV_FILE not found"
    print_info "Please run deploy.sh first to configure the system"
    exit 1
fi

# Read current configuration from deploy file
CURRENT_PORT=$(grep "^API_PORT=" "$DEPLOY_ENV_FILE" | cut -d'=' -f2)

if [[ -z "$CURRENT_PORT" ]]; then
    print_error "API_PORT not found in $DEPLOY_ENV_FILE"
    exit 1
fi

# Generate new secure tokens
API_SECRET_KEY=$(openssl rand -base64 32 | tr -d '\n' | tr -d '=+/')
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n' | tr -d '=+/')

print_info "Generated new security tokens"

# Update deploy environment file with new tokens
sed -i "s|^API_SECRET_KEY=.*|API_SECRET_KEY=$API_SECRET_KEY|" "$DEPLOY_ENV_FILE"
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" "$DEPLOY_ENV_FILE"

print_success "Updated deploy environment file: $DEPLOY_ENV_FILE"

# Restart service to apply new tokens
print_info "Restarting service to apply new tokens..."
if systemctl restart $SERVICE_NAME; then
    print_success "Service restarted successfully"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Service is running with new tokens"
        print_info "Service status:"
        systemctl status $SERVICE_NAME --no-pager -l
    else
        print_error "Service failed to start with new tokens"
        print_info "Checking logs:"
        journalctl -u $SERVICE_NAME --no-pager -l -n 20
        exit 1
    fi
else
    print_error "Failed to restart service"
    print_info "Checking logs:"
    journalctl -u $SERVICE_NAME --no-pager -l -n 20
    exit 1
fi

print_info "Security tokens have been regenerated and service restarted"
print_warning "Note: All existing API sessions will be invalidated"
print_info "New tokens are stored in: $DEPLOY_ENV_FILE" 