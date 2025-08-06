#!/bin/bash
# Complete OpenVPN Manager Deployment Script
# Installs CLI, API, and Web Panel with full system integration

# Enable debugging and exit on error
set -e
set -x

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="openvpn"
API_PORT="5000"
API_SERVICE_NAME="openvpn-api"
MONITOR_SERVICE_NAME="openvpn-monitor"

# Colors for output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# --- Functions ---
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    [ "$EUID" -ne 0 ] && { print_error "This script must be run with root privileges. Please use 'sudo'."; exit 1; }
}

install_system_packages() {
    print_status "Installing system packages..."
    export DEBIAN_FRONTEND=noninteractive
    
    print_status "Updating package lists..."
    if ! apt-get update -qq; then
        print_error "Failed to update package lists"
        exit 1
    fi
    
    print_status "Installing required packages..."
    if ! apt-get install -y -qq git python3 python3-pip python3-venv curl sqlite3 ufw systemd; then
        print_error "Failed to install system packages"
        exit 1
    fi
    
    print_success "System packages installed"
}

setup_project() {
    print_status "Setting up project files..."
    cd /opt
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Project directory exists. Updating..."
        cd "$PROJECT_DIR"
        if ! git reset --hard HEAD >/dev/null 2>&1; then
            print_error "Failed to reset git repository"
            exit 1
        fi
        if ! git pull origin main >/dev/null 2>&1; then
            print_error "Failed to pull latest changes"
            exit 1
        fi
    else
        print_status "Cloning project repository..."
        if ! git clone "$REPO_URL" "$PROJECT_DIR" >/dev/null 2>&1; then
            print_error "Failed to clone repository from $REPO_URL"
            print_error "Please check your internet connection and try again"
            exit 1
        fi
        cd "$PROJECT_DIR"
    fi
    
    chown -R root:root /opt/$PROJECT_DIR
    chmod -R 755 /opt/$PROJECT_DIR
    export PROJECT_ROOT="/opt/$PROJECT_DIR"
    print_success "Project files ready at $PROJECT_ROOT"
}

setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    cd /opt/$PROJECT_DIR
    
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        if ! python3 -m venv venv >/dev/null 2>&1; then
            print_error "Failed to create Python virtual environment"
            exit 1
        fi
    fi
    
    print_status "Activating virtual environment..."
    if ! source venv/bin/activate; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
    
    print_status "Upgrading pip..."
    if ! pip install --upgrade pip -q >/dev/null 2>&1; then
        print_error "Failed to upgrade pip"
        exit 1
    fi
    
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        if ! pip install -r requirements.txt -q >/dev/null 2>&1; then
            print_error "Failed to install Python dependencies"
            exit 1
        fi
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    print_status "Setting execute permissions..."
    chmod +x cli/main.py api/app.py scripts/*.py 2>/dev/null || true
    print_success "Python environment configured"
}

setup_frontend() {
    print_status "Setting up frontend (Web Panel)..."
    cd /opt/$PROJECT_DIR/frontend
    
    if [ ! -d "dist" ]; then
        print_error "Pre-built frontend not found! The dist directory is missing."
        print_error "This should not happen with the static frontend implementation."
        exit 1
    fi
    
    REQUIRED_FILES=("dist/index.html" "dist/assets/css/main.css" "dist/assets/js/app.js")
    for file in "${REQUIRED_FILES[@]}"; do
        [ ! -f "$file" ] && { print_error "Required frontend file missing: $file"; exit 1; }
    done
    
    print_success "✅ Pre-built static frontend verified"
    chown -R root:root dist/ && find dist/ -type d -exec chmod 755 {} \; && find dist/ -type f -exec chmod 644 {} \;
    print_success "Frontend ready to serve via Flask (no build process required)"
    print_status "📦 Frontend size: $(du -sh dist | cut -f1) | 🚀 Features: Multi-language, Dark/Light themes, Mobile responsive, PWA ready"
}

create_services() {
    print_status "Creating systemd services..."
    
    # API Service
    cat > /etc/systemd/system/${API_SERVICE_NAME}.service << EOF
[Unit]
Description=OpenVPN Manager API
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/${PROJECT_DIR}
Environment=PROJECT_ROOT=/opt/${PROJECT_DIR}
Environment=OPENVPN_API_KEY=openvpn_$(openssl rand -hex 16)
ExecStart=/opt/${PROJECT_DIR}/venv/bin/python -m api.app
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=openvpn-api

[Install]
WantedBy=multi-user.target
EOF
    
    # Monitor Service
    cat > /etc/systemd/system/${MONITOR_SERVICE_NAME}.service << EOF
[Unit]
Description=OpenVPN Traffic Monitor
After=network.target openvpn-api.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/${PROJECT_DIR}
Environment=PROJECT_ROOT=/opt/${PROJECT_DIR}
ExecStart=/opt/${PROJECT_DIR}/venv/bin/python scripts/monitor_service.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=openvpn-monitor

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${API_SERVICE_NAME} ${MONITOR_SERVICE_NAME}
    print_success "Services created and enabled"
}

setup_database() {
    print_status "Setting up database..."
    cd /opt/$PROJECT_DIR
    mkdir -p /opt/$PROJECT_DIR/data/db
    
    if [ ! -f "/opt/$PROJECT_DIR/data/db/openvpn.db" ]; then
        source venv/bin/activate
        sqlite3 /opt/$PROJECT_DIR/data/db/openvpn.db < database.sql
    fi
    
    chown -R root:root /opt/$PROJECT_DIR/data && chmod -R 750 /opt/$PROJECT_DIR/data
    print_success "Database initialized"
}

configure_firewall() {
    print_status "Configuring firewall..."
    echo 'y' | ufw --force enable >/dev/null 2>&1
    ufw allow ssh >/dev/null 2>&1
    ufw allow ${API_PORT}/tcp >/dev/null 2>&1
    ufw allow 1194/udp >/dev/null 2>&1
    ufw allow 1195/udp >/dev/null 2>&1
    print_success "Firewall configured"
}

generate_and_start() {
    print_status "Generating API key and starting services..."
    
    API_KEY="openvpn_$(openssl rand -hex 16)"
    sed -i "s/Environment=OPENVPN_API_KEY=.*/Environment=OPENVPN_API_KEY=${API_KEY}/" /etc/systemd/system/${API_SERVICE_NAME}.service
    systemctl daemon-reload
    
    echo "OPENVPN_API_KEY=${API_KEY}" > /opt/$PROJECT_DIR/environment.env
    chmod 600 /opt/$PROJECT_DIR/environment.env
    
    systemctl start ${API_SERVICE_NAME} ${MONITOR_SERVICE_NAME}
    sleep 5
    
    print_success "API key generated and services started"
}

verify_and_display() {
    print_status "Verifying installation..."
    
    # Check services
    systemctl is-active --quiet ${API_SERVICE_NAME} && print_success "Flask application is running" || print_error "Flask application is not running"
    systemctl is-active --quiet ${MONITOR_SERVICE_NAME} && print_success "Monitor service is running" || print_error "Monitor service is not running"
    
    # Test endpoints
    sleep 3
    timeout 10 curl -s http://localhost:${API_PORT}/api/health > /dev/null 2>&1 && print_success "API is responding" || print_warning "API may not be ready yet"
    timeout 10 curl -s http://localhost:${API_PORT}/ > /dev/null 2>&1 && print_success "Web panel is accessible" || print_warning "Web panel may not be ready yet"
    
    # Display access info
    echo ""
    echo "=================================================="
    echo -e "${GREEN}🎉 OpenVPN Manager Installation Complete!${NC}"
    echo "=================================================="
    echo ""
    echo -e "${BLUE}📱 Access Information:${NC}"
    SERVER_IP=$(timeout 5 curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' || echo 'YOUR_SERVER_IP')
    echo "   URL: http://${SERVER_IP}:${API_PORT}"
    echo "   Local: http://localhost:${API_PORT}"
    echo ""
    echo -e "${BLUE}🔑 API Key for Login:${NC}"
    echo "   $(cat /opt/$PROJECT_DIR/environment.env | grep OPENVPN_API_KEY | cut -d'=' -f2)"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo "   CLI: cd /opt/${PROJECT_DIR} && source venv/bin/activate && python -m cli.main"
    echo "   App Logs: journalctl -u ${API_SERVICE_NAME} -f"
    echo "   Monitor Logs: journalctl -u ${MONITOR_SERVICE_NAME} -f"
    echo ""
    echo -e "${YELLOW}⚠️  Important Notes:${NC}"
    echo "   - Everything runs on port ${API_PORT} (single Flask app)"
    echo "   - Web panel and API are served together"
    echo "   - Use the API key above to login to web panel"
    echo "   - Optimized for low-resource servers"
    echo ""
}

complete_installation() {
    print_status "Starting complete OpenVPN Manager installation..."
    
    print_status "Step 1/10: Checking root privileges..."
    check_root
    
    print_status "Step 2/10: Installing system packages..."
    install_system_packages
    
    print_status "Step 3/10: Setting up project files..."
    setup_project
    
    print_status "Step 4/10: Configuring Python environment..."
    setup_python_environment
    
    print_status "Step 5/10: Setting up database..."
    setup_database
    
    print_status "Step 6/10: Setting up frontend..."
    setup_frontend
    
    print_status "Step 7/10: Creating services..."
    create_services
    
    print_status "Step 8/10: Configuring firewall..."
    configure_firewall
    
    print_status "Step 9/10: Starting services..."
    generate_and_start
    
    print_status "Step 10/10: Verifying installation..."
    verify_and_display
}

uninstall_system() {
    print_warning "This will completely remove OpenVPN Manager..."
    read -p "Are you sure? This cannot be undone! [y/N]: " confirm
    
    if [[ "$confirm" =~ ^[yY](es)?$ ]]; then
        print_status "Uninstalling OpenVPN Manager..."
        
        systemctl stop ${API_SERVICE_NAME} ${MONITOR_SERVICE_NAME} 2>/dev/null || true
        systemctl disable ${API_SERVICE_NAME} ${MONITOR_SERVICE_NAME} 2>/dev/null || true
        rm -f /etc/systemd/system/${API_SERVICE_NAME}.service /etc/systemd/system/${MONITOR_SERVICE_NAME}.service
        systemctl daemon-reload
        rm -rf /opt/${PROJECT_DIR}
        
        print_success "OpenVPN Manager uninstalled"
    else
        print_status "Uninstall cancelled"
    fi
}

main_menu() {
    echo ""
    echo "========================================="
    echo "   OpenVPN Manager Deployment Tool"
    echo "========================================="
    echo "1) Complete Installation (CLI + API + Web Panel)"
    echo "2) Uninstall System"
    echo "3) View Service Status"
    echo "4) Exit"
    echo ""
    read -p "Select an option [1-4]: " choice
    
    case $choice in
        1) complete_installation ;;
        2) uninstall_system ;;
        3) 
            print_status "Service Status:"
            systemctl status ${API_SERVICE_NAME} --no-pager -l 2>/dev/null || echo "Flask app service not found"
            systemctl status ${MONITOR_SERVICE_NAME} --no-pager -l 2>/dev/null || echo "Monitor service not found"
            ;;
        4) print_status "Exiting..."; exit 0 ;;
        *) print_error "Invalid option. Please try again."; main_menu ;;
    esac
}

# Main execution
cd /tmp && main_menu