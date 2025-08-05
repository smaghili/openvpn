"""
Type definitions for VPN Manager project.
Provides type safety and better IDE support.
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Type aliases for better readability
Username = str
Password = str
FilePath = str
ConfigData = str
IPAddress = str
Port = int

class AuthType(Enum):
    """Authentication types supported by the VPN system."""
    CERTIFICATE = "certificate"
    LOGIN = "login"

class Protocol(Enum):
    """Network protocols supported."""
    UDP = "udp"
    TCP = "tcp"

class DNSProvider(Enum):
    """DNS provider options."""
    SYSTEM = "1"
    UNBOUND = "2"
    CLOUDFLARE = "3"
    GOOGLE = "4"
    ADGUARD = "5"

@dataclass
class InstallSettings:
    """Installation settings with type safety."""
    public_ip: IPAddress
    cert_port: Port
    cert_proto: str
    login_port: Port
    login_proto: str
    dns: str
    cipher: str
    cert_size: str

@dataclass
class UserData:
    """User data structure with type information."""
    id: int
    username: Username
    password_hash: Optional[str]
    status: str
    created_at: str
    updated_at: str
    auth_type: Optional[str] = None
    protocol: Optional[str] = None
    cert_pem: Optional[str] = None
    key_pem: Optional[str] = None

# Database query result type
DatabaseRow = Dict[str, Any]
DatabaseResult = List[DatabaseRow]

# Configuration dictionary type
ConfigDict = Dict[str, Union[str, int, bool]]