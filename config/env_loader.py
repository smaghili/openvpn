#!/usr/bin/env python3
"""
Environment configuration loader for OpenVPN Traffic Monitor
Loads configuration from .env file if it exists
"""
import os

def load_env_file(env_file_path=None):
    """
    Load environment variables from a .env file
    
    Args:
        env_file_path (str): Path to the environment file. 
                           If None, looks for '.env' in project root.
    """
    if env_file_path is None:
        # Get project root directory
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        env_file_path = os.path.join(project_root, '.env')
    
    if not os.path.exists(env_file_path):
        return  # No env file, use system environment variables
    
    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Only set if not already set in system environment
                    if key not in os.environ:
                        os.environ[key] = value
                        
    except Exception as e:
        # Silently ignore errors to prevent breaking the service
        pass

def get_config_value(key, default=None):
    """
    Get a configuration value with fallback to default
    
    Args:
        key (str): Environment variable name
        default: Default value if not found
        
    Returns:
        Configuration value
    """
    return os.environ.get(key, default)

def get_int_config(key, default=0):
    """
    Get an integer configuration value
    
    Args:
        key (str): Environment variable name
        default (int): Default value if not found or invalid
        
    Returns:
        int: Configuration value
    """
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

# Load environment file when this module is imported
load_env_file()