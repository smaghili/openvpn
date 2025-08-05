#!/bin/bash
# A streamlined deployment script for the VPN Manager application.
# This script prepares the environment and hands over control to the Python application.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
REPO_URL="https://github.com/smaghili/openvpn.git"
PROJECT_DIR="openvpn" # The directory where the project will be cloned

# --- Functions ---

function check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ This script must be run with root privileges. Please use 'sudo'."
        exit 1
    fi
}

function install_deployment() {
    echo "▶️  Starting VPN Manager deployment..."
    check_root
    echo "[1/4] Installing base system packages (git, python3-venv)..."
    apt-get update
    apt-get install -y git python3-venv

    echo "[2/4] Syncing project files from repository..."
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
    echo "[3/4] Setting up Python environment..."
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

    echo "[4/4] Launching the application's main installer..."
    echo "--------------------------------------------------------"
    export PROJECT_ROOT="$(pwd)"
    echo "      -> Project root set to: $PROJECT_ROOT"
    sudo PROJECT_ROOT="$PROJECT_ROOT" "venv/bin/python" -m cli.main
}

function remove_project_files() {
    echo "▶️  Removing project files..."
    echo "⚠️  This will ONLY remove the cloned project directory ('$PROJECT_DIR')."
    echo "To fully uninstall OpenVPN and system configurations, please run the"
    echo "application and use the 'Uninstall' option from the main menu."

    read -p "Are you sure you want to remove the '$PROJECT_DIR' directory? [y/N]: " confirm
    if [[ "$confirm" =~ ^[yY](es)?$ ]]; then
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
    echo "1) Deploy Application (Install or launch manager)"
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
