from dataclasses import dataclass
from typing import Optional
from core.types import Username

@dataclass
class User:
    id: int
    username: Username
    password_hash: Optional[str]
    status: str
    created_at: str
    updated_at: str

@dataclass
class UserProtocol:
    id: int
    user_id: int
    protocol: str
    auth_type: str
    cert_pem: Optional[str]
    key_pem: Optional[str]
    status: str
    created_at: str
    updated_at: str