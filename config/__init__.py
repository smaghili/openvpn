# Configuration module exports
from .config import VPNConfig, config
from .shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
from .paths import VPNPaths, paths

__all__ = [
    'VPNConfig',
    'config', 
    'CLIENT_TEMPLATE',
    'USER_CERTS_TEMPLATE',
    'VPNPaths',
    'paths'
]
