#!/bin/bash
# A streamlined deployment script for the VPN Manager application.
# This script prepares the environment and hands over control to the Python application.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="openvpn" # The directory where the project will be cloned

# --- Functions ---

function check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "❌ This script must be run with root privileges. Please use 'sudo'."
        exit 1
    fi
}

function install_deployment() {
    echo "▶️  Starting VPN Manager deployment..."
    check_root
    echo "[1/5] Installing base system packages (git, python3-venv)..."
    apt-get update
    apt-get install -y git python3-venv

    echo "[2/5] Syncing project files from repository..."
    if [ -d "$PROJECT_DIR" ]; then
        echo "      -> Project directory exists. Fetching latest version..."
        cd "$PROJECT_DIR"
        git reset --hard HEAD
        git pull origin main
    else
        echo "      -> Cloning new copy of the project..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    echo "[3/5] Setting up Python environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    . "venv/bin/activate"
    pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        pip install -r "requirements.txt"
    else
        echo "      -> WARNING: requirements.txt not found. Dependencies may be missing."
    fi

    echo "[4/5] Launching the application's main installer (CLI + OpenVPN)..."
    echo "--------------------------------------------------------"
    export PROJECT_ROOT="$(pwd)"
    echo "      -> Project root set to: $PROJECT_ROOT"
    
    # Ensure CLI script has execute permissions before launching
    chmod +x cli/main.py
    
    sudo PROJECT_ROOT="$PROJECT_ROOT" "venv/bin/python" -m cli.main
    
    echo "[5/5] Setting up Web Panel..."
    setup_web_panel
}

function setup_web_panel() {
    echo "▶️  Setting up Web Panel (API + Frontend)..."
    
    # Create systemd service for API
    cat > /etc/systemd/system/openvpn-api.service << EOF
[Unit]
Description=OpenVPN Manager API
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PWD
Environment=PROJECT_ROOT=$PWD
Environment=OPENVPN_API_KEY=openvpn_$(openssl rand -hex 16)
ExecStart=$PWD/venv/bin/python -m api.app
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=openvpn-api

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd service for monitor
    cat > /etc/systemd/system/openvpn-monitor.service << EOF
[Unit]
Description=OpenVPN Traffic Monitor
After=network.target openvpn-api.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PWD
Environment=PROJECT_ROOT=$PWD
ExecStart=$PWD/venv/bin/python scripts/monitor_service.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=openvpn-monitor

[Install]
WantedBy=multi-user.target
EOF

    # Generate API key and save it
    API_KEY="openvpn_$(openssl rand -hex 16)"
    echo "OPENVPN_API_KEY=$API_KEY" > environment.env
    chmod 600 environment.env
    
    # Update service with actual API key
    sed -i "s/Environment=OPENVPN_API_KEY=.*/Environment=OPENVPN_API_KEY=$API_KEY/" /etc/systemd/system/openvpn-api.service
    
    # Enable and start services
    systemctl daemon-reload
    systemctl enable openvpn-api openvpn-monitor
    systemctl start openvpn-api openvpn-monitor
    
    # Configure firewall
    ufw allow 5000/tcp >/dev/null 2>&1 || true
    
    echo "✅ Web Panel setup complete!"
    echo ""
    echo "🌐 ACCESS INFORMATION:"
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' || echo 'YOUR_SERVER_IP')
    echo "   Web Panel: http://$SERVER_IP:5000"
    echo "   API Key: $API_KEY"
    echo ""
    echo "📋 MANAGEMENT:"
    echo "   CLI: cd $PWD && source venv/bin/activate && python -m cli.main"
    echo "   API Logs: journalctl -u openvpn-api -f"
    echo "   Monitor Logs: journalctl -u openvpn-monitor -f"
    echo ""
}

function remove_project_files() {
    echo "▶️  Removing project files..."
    echo "⚠️  This will ONLY remove the cloned project directory ('$PROJECT_DIR')."
    echo "To fully uninstall OpenVPN and system configurations, please run the"
    echo "application and use the 'Uninstall' option from the main menu."

    read -p "Are you sure you want to remove the '$PROJECT_DIR' directory? [y/N]: " confirm
    if [[ "$confirm" =~ ^[yY](es)?$ ]]; then
        # Stop services if they exist
        systemctl stop openvpn-api openvpn-monitor 2>/dev/null || true
        systemctl disable openvpn-api openvpn-monitor 2>/dev/null || true
        rm -f /etc/systemd/system/openvpn-api.service /etc/systemd/system/openvpn-monitor.service 2>/dev/null || true
        systemctl daemon-reload
        
        # Go up one level to be able to remove the directory
        cd ..
        if [ -d "$PROJECT_DIR" ]; then
            rm -rf "$PROJECT_DIR"
            echo "✅ Project directory removed."
        else
            echo "Directory not found."
        fi
    else
        echo "Operation cancelled."
    fi
}

function main() {
    echo "--- VPN Manager Deployment Utility ---"
    echo "1) Deploy Application (CLI + OpenVPN + Web Panel)"
    echo "2) Remove Project Directory"
    echo "3) Exit"
    read -p "Select an option: " choice

    case $choice in
        1)
            install_deployment
            ;;
        2)
            remove_project_files
            ;;
        3)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            main
            ;;
    esac
}

# Ensure the script is executed from the user's home directory or a safe location
cd ~
main