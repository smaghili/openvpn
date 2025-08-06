#!/bin/bash
# Complete OpenVPN Manager Deployment Script
# Installs CLI, API, and Web Panel with full system integration

set -e

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="openvpn"
API_PORT="5000"
WEB_PORT="3000"
API_SERVICE_NAME="openvpn-api"
MONITOR_SERVICE_NAME="openvpn-monitor"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Functions ---

function print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run with root privileges. Please use 'sudo'."
        exit 1
    fi
}

function install_system_packages() {
    print_status "Installing system packages..."
    apt-get update
    apt-get install -y \
        git \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        nodejs \
        npm \
        sqlite3 \
        ufw \
        systemd
    print_success "System packages installed"
}

function setup_project() {
    print_status "Setting up project files..."
    cd /opt
    
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "Project directory exists. Updating..."
        cd "$PROJECT_DIR"
        git reset --hard HEAD
        git pull origin main
    else
        print_status "Cloning project repository..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    # Set proper ownership
    chown -R root:root /opt/$PROJECT_DIR
    chmod -R 755 /opt/$PROJECT_DIR
    
    export PROJECT_ROOT="/opt/$PROJECT_DIR"
    print_success "Project files ready at $PROJECT_ROOT"
}

function setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    cd /opt/$PROJECT_DIR
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    # Set execute permissions on Python scripts
    chmod +x cli/main.py
    chmod +x api/app.py
    chmod +x scripts/monitor_service.py
    chmod +x scripts/on_connect.py
    chmod +x scripts/on_disconnect.py
    
    print_success "Python environment configured"
}

function setup_frontend() {
    print_status "Setting up frontend (Web Panel)..."
    cd /opt/$PROJECT_DIR/frontend
    
    # Install Node.js dependencies
    npm install
    
    # Build for production
    npm run build
    
    # Ensure dist directory has proper permissions
    chown -R root:root dist/
    chmod -R 755 dist/
    
    print_success "Frontend built and ready to serve via Flask"
}

function create_api_service() {
    print_status "Creating API systemd service..."
    
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
    
    systemctl daemon-reload
    systemctl enable ${API_SERVICE_NAME}
    
    print_success "API service created"
}

function create_monitor_service() {
    print_status "Creating monitoring service..."
    
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
    systemctl enable ${MONITOR_SERVICE_NAME}
    
    print_success "Monitor service created"
}

function setup_database() {
    print_status "Setting up database..."
    cd /opt/$PROJECT_DIR
    
    # Create data directory
    mkdir -p /opt/$PROJECT_DIR/data/db
    
    # Initialize database if it doesn't exist
    if [ ! -f "/opt/$PROJECT_DIR/data/db/openvpn.db" ]; then
        source venv/bin/activate
        sqlite3 /opt/$PROJECT_DIR/data/db/openvpn.db < database.sql
    fi
    
    # Set proper permissions
    chown -R root:root /opt/$PROJECT_DIR/data
    chmod -R 750 /opt/$PROJECT_DIR/data
    
    print_success "Database initialized"
}

function configure_firewall() {
    print_status "Configuring firewall..."
    
    # Allow SSH, Flask app, and OpenVPN ports
    ufw --force enable
    ufw allow ssh
    ufw allow ${API_PORT}/tcp
    ufw allow 1194/udp
    ufw allow 1195/udp
    
    print_success "Firewall configured"
}

function start_services() {
    print_status "Starting services..."
    
    # Start API service (includes web panel)
    systemctl start ${API_SERVICE_NAME}
    sleep 3
    
    # Start monitor service
    systemctl start ${MONITOR_SERVICE_NAME}
    sleep 2
    
    print_success "All services started"
}

function generate_api_key() {
    print_status "Generating API key..."
    
    API_KEY="openvpn_$(openssl rand -hex 16)"
    
    # Update service environment
    sed -i "s/Environment=OPENVPN_API_KEY=.*/Environment=OPENVPN_API_KEY=${API_KEY}/" /etc/systemd/system/${API_SERVICE_NAME}.service
    systemctl daemon-reload
    
    # Save to environment file
    echo "OPENVPN_API_KEY=${API_KEY}" > /opt/$PROJECT_DIR/environment.env
    chmod 600 /opt/$PROJECT_DIR/environment.env
    
    print_success "API key generated: ${API_KEY}"
}

function verify_installation() {
    print_status "Verifying installation..."
    
    # Check services status
    if systemctl is-active --quiet ${API_SERVICE_NAME}; then
        print_success "Flask application is running"
    else
        print_error "Flask application is not running"
    fi
    
    if systemctl is-active --quiet ${MONITOR_SERVICE_NAME}; then
        print_success "Monitor service is running"
    else
        print_error "Monitor service is not running"
    fi
    
    # Test API endpoint
    sleep 3
    if curl -s http://localhost:${API_PORT}/api/health > /dev/null; then
        print_success "API is responding"
    else
        print_warning "API may not be ready yet"
    fi
    
    # Test web panel
    if curl -s http://localhost:${API_PORT}/ > /dev/null; then
        print_success "Web panel is accessible"
    else
        print_warning "Web panel may not be ready yet"
    fi
}

function display_access_info() {
    echo ""
    echo "=================================================="
    echo -e "${GREEN}🎉 OpenVPN Manager Installation Complete!${NC}"
    echo "=================================================="
    echo ""
    echo -e "${BLUE}📱 Web Panel & API Access:${NC}"
    echo "   URL: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):${API_PORT}"
    echo "   Local: http://localhost:${API_PORT}"
    echo ""
    echo -e "${BLUE}🔗 Endpoints:${NC}"
    echo "   Web Panel: http://YOUR_IP:${API_PORT}/"
    echo "   API: http://YOUR_IP:${API_PORT}/api/"
    echo ""
    echo -e "${BLUE}🔑 API Key for Login:${NC}"
    echo "   $(cat /opt/$PROJECT_DIR/environment.env | grep OPENVPN_API_KEY | cut -d'=' -f2)"
    echo ""
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo "   Flask App: systemctl status ${API_SERVICE_NAME}"
    echo "   Monitor: systemctl status ${MONITOR_SERVICE_NAME}"
    echo ""
    echo -e "${BLUE}📁 Important Paths:${NC}"
    echo "   Project: /opt/${PROJECT_DIR}"
    echo "   Frontend: /opt/${PROJECT_DIR}/frontend/dist"
    echo "   Database: /opt/${PROJECT_DIR}/data/db/openvpn.db"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo "   CLI Access: cd /opt/${PROJECT_DIR} && source venv/bin/activate && python -m cli.main"
    echo "   View App Logs: journalctl -u ${API_SERVICE_NAME} -f"
    echo "   View Monitor Logs: journalctl -u ${MONITOR_SERVICE_NAME} -f"
    echo ""
    echo -e "${YELLOW}⚠️  Important Notes:${NC}"
    echo "   - Everything runs on port ${API_PORT} (single Flask app)"
    echo "   - Web panel and API are served together"
    echo "   - Use the API key above to login to web panel"
    echo "   - SSL is disabled as requested"
    echo "   - Optimized for low-resource servers"
    echo ""
}

function complete_installation() {
    print_status "Starting complete OpenVPN Manager installation..."
    
    check_root
    install_system_packages
    setup_project
    setup_python_environment
    setup_database
    setup_frontend
    generate_api_key
    create_api_service
    create_monitor_service
    configure_firewall
    start_services
    verify_installation
    display_access_info
}

function uninstall_system() {
    print_warning "This will completely remove OpenVPN Manager..."
    read -p "Are you sure? This cannot be undone! [y/N]: " confirm
    
    if [[ "$confirm" =~ ^[yY](es)?$ ]]; then
        print_status "Uninstalling OpenVPN Manager..."
        
        # Stop services
        systemctl stop ${API_SERVICE_NAME} 2>/dev/null || true
        systemctl stop ${MONITOR_SERVICE_NAME} 2>/dev/null || true
        systemctl disable ${API_SERVICE_NAME} 2>/dev/null || true
        systemctl disable ${MONITOR_SERVICE_NAME} 2>/dev/null || true
        
        # Remove service files
        rm -f /etc/systemd/system/${API_SERVICE_NAME}.service
        rm -f /etc/systemd/system/${MONITOR_SERVICE_NAME}.service
        systemctl daemon-reload
        
        # Remove project files
        rm -rf /opt/${PROJECT_DIR}
        
        print_success "OpenVPN Manager uninstalled"
    else
        print_status "Uninstall cancelled"
    fi
}

function main_menu() {
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
        1)
            complete_installation
            ;;
        2)
            uninstall_system
            ;;
        3)
            print_status "Service Status:"
            systemctl status ${API_SERVICE_NAME} --no-pager -l || echo "Flask app service not found"
            systemctl status ${MONITOR_SERVICE_NAME} --no-pager -l || echo "Monitor service not found"
            ;;
        4)
            print_status "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid option. Please try again."
            main_menu
            ;;
    esac
}

# Main execution
cd /tmp
main_menu
