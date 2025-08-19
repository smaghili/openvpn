# Configuration module exports
from .config import VPNConfig
from .shared_config import CLIENT_TEMPLATE, USER_CERTS_TEMPLATE
from .paths import VPNPaths, paths

__all__ = [
    'VPNConfig',
    'CLIENT_TEMPLATE',
    'USER_CERTS_TEMPLATE',
    'VPNPaths',
    'paths'
]
