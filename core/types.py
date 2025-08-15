"""
Type definitions for VPN Manager project.
Provides type safety and better IDE support.
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from enum import Enum

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


DatabaseRow = Dict[str, Any]
DatabaseResult = List[DatabaseRow]
ConfigDict = Dict[str, Union[str, int, bool]]