"""
JWT service for secure authentication with token versioning and blacklist management.
"""

import jwt
import uuid
import time
import os
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from core.exceptions import ValidationError, AuthenticationError

class JWTService:
    """
    Lightweight JWT service with security controls for OpenVPN Manager.
    Provides token generation, validation, and revocation capabilities.
    """
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = 'HS256'
        self.token_expiry_hours = 24
        self._blacklisted_tokens: Set[str] = set()
        self._max_blacklist_size = 1000
    
    def generate_token(self, admin_id: int, username: str, role: str, token_version: int) -> Dict[str, Any]:
        """
        Generate JWT token with unique tracking ID and version control.
        """
        now = datetime.utcnow()
        token_id = str(uuid.uuid4())
        
        payload = {
            'jti': token_id,
            'admin_id': admin_id,
            'username': username,
            'role': role,
            'token_version': token_version,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=self.token_expiry_hours)).timestamp())
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            'token': token,
            'token_id': token_id,
            'expires_in': self.token_expiry_hours * 3600,
            'expires_at': payload['exp']
        }
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token with comprehensive security checks.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            token_id = payload.get('jti')
            if not token_id:
                raise AuthenticationError("Token missing unique identifier")
            
            if self.is_token_blacklisted(token_id):
                raise AuthenticationError("Token has been revoked")
            
            required_fields = ['admin_id', 'username', 'role', 'token_version']
            for field in required_fields:
                if field not in payload:
                    raise AuthenticationError(f"Token missing required field: {field}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    def blacklist_token(self, token_id: str) -> None:
        """
        Add token to in-memory blacklist with size management.
        """
        if len(self._blacklisted_tokens) >= self._max_blacklist_size:
            oldest_tokens = list(self._blacklisted_tokens)[:100]
            for old_token in oldest_tokens:
                self._blacklisted_tokens.discard(old_token)
        
        self._blacklisted_tokens.add(token_id)
    
    def is_token_blacklisted(self, token_id: str) -> bool:
        """
        Check if token is blacklisted in memory cache.
        """
        return token_id in self._blacklisted_tokens
    
    def get_token_payload_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract token payload without validation for revocation purposes.
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None
    
    def validate_token_version(self, token_version: int, current_version: int) -> bool:
        """
        Validate token version against current admin version.
        """
        return token_version == current_version
    
    @staticmethod
    def create_service() -> 'JWTService':
        """
        Factory method to create JWT service with environment configuration.
        """
        secret_key = os.environ.get('JWT_SECRET')
        if not secret_key:
            raise ValidationError("JWT_SECRET environment variable not configured")
        
        if len(secret_key) < 32:
            raise ValidationError("JWT_SECRET must be at least 32 characters long")
        
        return JWTService(secret_key)