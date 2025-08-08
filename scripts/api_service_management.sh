#!/bin/bash

# OpenVPN API Service Management Script

SERVICE_NAME="openvpn-api"

case "$1" in
    start)
        echo "Starting OpenVPN API service..."
        systemctl start $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager -l
        ;;
    stop)
        echo "Stopping OpenVPN API service..."
        systemctl stop $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager -l
        ;;
    restart)
        echo "Restarting OpenVPN API service..."
        systemctl restart $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager -l
        ;;
    status)
        echo "OpenVPN API service status:"
        systemctl status $SERVICE_NAME --no-pager -l
        ;;
    logs)
        echo "Showing OpenVPN API service logs (press Ctrl+C to exit):"
        journalctl -u $SERVICE_NAME -f
        ;;
    enable)
        echo "Enabling OpenVPN API service..."
        systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "Disabling OpenVPN API service..."
        systemctl disable $SERVICE_NAME
        ;;
    install)
        echo "Installing OpenVPN API service..."
        bash scripts/install_api_service.sh
        ;;
    regenerate-tokens)
        echo "Regenerating security tokens..."
        bash scripts/regenerate_tokens.sh
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable|install|regenerate-tokens}"
        echo ""
        echo "Commands:"
        echo "  start             - Start the API service"
        echo "  stop              - Stop the API service"
        echo "  restart           - Restart the API service"
        echo "  status            - Show service status"
        echo "  logs              - Show service logs (follow mode)"
        echo "  enable            - Enable service auto-start"
        echo "  disable           - Disable service auto-start"
        echo "  install           - Install the service"
        echo "  regenerate-tokens - Generate new security tokens"
        exit 1
        ;;
esac 