#!/bin/bash
# Deployment script for OpenVPN monitoring system
# This script sets up the monitoring service properly

set -e

PROJECT_ROOT="/home/seyed/Cursor Project/openvpn"
SERVICE_FILE="openvpn-monitor.service"
LOG_DIR="/var/log/openvpn"

echo "🚀 Deploying OpenVPN Monitor Service"
echo "===================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

# Create log directory if it doesn't exist
echo "📁 Creating log directory..."
mkdir -p "$LOG_DIR"
chown root:root "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Create the log file with proper permissions
touch "$LOG_DIR/traffic_monitor.log"
chown root:root "$LOG_DIR/traffic_monitor.log"
chmod 644 "$LOG_DIR/traffic_monitor.log"

# Copy and install the systemd service
echo "⚙️  Installing systemd service..."
cp "$PROJECT_ROOT/$SERVICE_FILE" /etc/systemd/system/

# Update the service file with the correct paths
sed -i "s|/home/seyed/Cursor Project/openvpn|$PROJECT_ROOT|g" /etc/systemd/system/$SERVICE_FILE

# Reload systemd and enable the service
systemctl daemon-reload
systemctl enable openvpn-monitor.service

# Verify Python dependencies
echo "🔍 Verifying system requirements..."
cd "$PROJECT_ROOT"
python3 -c "import sqlite3, socket, time, os, sys, datetime" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All Python dependencies are available!"
else
    echo "❌ Missing Python dependencies!"
    exit 1
fi

# Start the service
echo "🔄 Starting monitor service..."
systemctl start openvpn-monitor.service

# Check service status
sleep 2
if systemctl is-active --quiet openvpn-monitor.service; then
    echo "✅ Monitor service is running successfully!"
    echo ""
    echo "📊 Service Status:"
    systemctl status openvpn-monitor.service --no-pager -l
    echo ""
    echo "📝 To view logs:"
    echo "   journalctl -u openvpn-monitor.service -f"
    echo "   tail -f $LOG_DIR/traffic_monitor.log"
    echo ""
    echo "⚙️  Configuration:"
    echo "   Monitor interval: $(systemctl show openvpn-monitor.service -p Environment | grep MONITOR_INTERVAL | cut -d= -f3) seconds"
    echo "   Max log size: $(systemctl show openvpn-monitor.service -p Environment | grep MAX_LOG_SIZE | cut -d= -f3) bytes"
    echo ""
    echo "🎉 Deployment completed successfully!"
else
    echo "❌ Monitor service failed to start!"
    echo "Check the logs:"
    journalctl -u openvpn-monitor.service --no-pager -l
    exit 1
fi