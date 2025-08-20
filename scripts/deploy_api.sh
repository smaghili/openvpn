#!/bin/bash

# OpenVPN Manager API Deployment Script
# This script sets up the API server as a systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_SERVICE_FILE="$PROJECT_ROOT/api/openvpn-api.service"
SYSTEMD_SERVICE_PATH="/etc/systemd/system/openvpn-api.service"

print_status "Deploying OpenVPN Manager API..."

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install -r "$PROJECT_ROOT/requirements.txt"

# Generate secure API key if not set
if [ -z "$OPENVPN_API_KEY" ]; then
    print_warning "No API key found in environment"
    API_KEY=$(openssl rand -hex 32)
    print_status "Generated secure API key: $API_KEY"
    
    # Update service file with the generated key
    sed -i "s/your-secure-api-key-here/$API_KEY/g" "$API_SERVICE_FILE"
    
    echo ""
    print_warning "IMPORTANT: Save this API key securely!"
    echo "API Key: $API_KEY"
    echo ""
    echo "You will need this key to authenticate with the API."
    echo "Add the following header to your API requests:"
    echo "X-API-Key: $API_KEY"
    echo ""
fi

# Update service file paths
sed -i "s|/home/seyed/Cursor Project/openvpn|$PROJECT_ROOT|g" "$API_SERVICE_FILE"

# Copy service file to systemd
print_status "Installing systemd service..."
cp "$API_SERVICE_FILE" "$SYSTEMD_SERVICE_PATH"

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable openvpn-api.service

# Start the service
print_status "Starting OpenVPN API service..."
systemctl start openvpn-api.service

# Get API port from environment
API_PORT=$(grep "^API_PORT=" /etc/owpanel/.env 2>/dev/null | cut -d'=' -f2)
API_PORT=${API_PORT:-5000}  # Default to 5000 if not found

# Check service status
if systemctl is-active --quiet openvpn-api.service; then
    print_status "✅ OpenVPN API service is running successfully!"
    print_status "API is available at: http://localhost:$API_PORT"
    print_status "Health check: http://localhost:$API_PORT/api/health"
else
    print_error "❌ Failed to start OpenVPN API service"
    print_error "Check logs with: journalctl -u openvpn-api.service -f"
    exit 1
fi

print_status "Deployment completed successfully!"
echo ""
echo "API Endpoints:"
echo "  Health Check:    GET /api/health"
echo "  User Management: /api/users/*"
echo "  Quota Management: /api/quota/*"
echo "  System Management: /api/system/*"
echo ""
echo "For detailed API documentation, see the route files in api/routes/"