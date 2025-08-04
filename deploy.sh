#!/bin/bash
# A streamlined deployment script for the VPN Manager application.
# This script prepares the environment and hands over control to the Python application.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
# !!! IMPORTANT: Replace this with your actual repository URL !!!
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

    # 1. Install minimal system dependencies
    echo "[1/4] Installing base system packages (git, python3-venv)..."
    apt-get update
    apt-get install -y git python3-venv

    # 2. Clone the project repository
    echo "[2/4] Cloning project from repository..."
    if [ -d "$PROJECT_DIR" ]; then
        echo "      -> Project directory '$PROJECT_DIR' already exists. Skipping clone."
    else
        git clone "$REPO_URL" "$PROJECT_DIR"
    fi
    cd "$PROJECT_DIR"

    # 3. Set up Python virtual environment and install dependencies
    echo "[3/4] Setting up Python environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source "venv/bin/activate"
    pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        pip install -r "requirements.txt"
    else
        echo "      -> WARNING: requirements.txt not found. Dependencies may be missing."
    fi

    # 4. Hand over control to the Python application installer
    echo "[4/4] Launching the application's main installer..."
    echo "--------------------------------------------------------"
    # We must use the python from the venv but run it with sudo
    # so that it has the necessary permissions for system-wide changes.
    # The -m flag runs the package as a script, ensuring correct module resolution.
    sudo "venv/bin/python" -m cli.main

    echo "--------------------------------------------------------"
    echo "✅ Deployment script finished. The application has now taken over."
}

function remove_project_files() {
    echo "▶️  Removing project files..."
    echo "⚠️  This will ONLY remove the cloned project directory ('$PROJECT_DIR')."
    echo "To fully uninstall OpenVPN and system configurations, please run the"
    echo "application and use the 'Uninstall' option from the main menu."

    read -p "Are you sure you want to remove the '$PROJECT_DIR' directory? [y/N]: " confirm
    if [[ "$confirm" =~ ^[yY](es)?$ ]]; then
        if [ -d "../$PROJECT_DIR" ]; then
            rm -rf "../$PROJECT_DIR"
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

main
