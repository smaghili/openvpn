"""
Custom exception classes for VPN Manager.
Provides specific error handling and better debugging.
"""

class VPNManagerError(Exception):
    """Base exception for VPN Manager operations."""
    pass

class InstallationError(VPNManagerError):
    """Raised when VPN installation fails."""
    pass

class UserAlreadyExistsError(VPNManagerError):
    """Raised when trying to create a user that already exists."""
    
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User '{username}' already exists")

class UserNotFoundError(VPNManagerError):
    """Raised when trying to access a non-existent user."""
    
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User '{username}' not found")

class CertificateGenerationError(VPNManagerError):
    """Raised when certificate generation fails."""
    
    def __init__(self, username: str, reason: str):
        self.username = username
        self.reason = reason
        super().__init__(f"Certificate generation failed for '{username}': {reason}")

class DatabaseError(VPNManagerError):
    """Raised when database operations fail."""
    pass

class ConfigurationError(VPNManagerError):
    """Raised when configuration is invalid or missing."""
    pass

class BackupError(VPNManagerError):
    """Raised when backup operations fail."""
    pass

class RestoreError(VPNManagerError):
    """Raised when restore operations fail."""
    pass

class ServiceError(VPNManagerError):
    """Raised when system service operations fail."""
    
    def __init__(self, service_name: str, operation: str, reason: str):
        self.service_name = service_name
        self.operation = operation
        self.reason = reason
        super().__init__(f"Service '{service_name}' {operation} failed: {reason}")

class ValidationError(VPNManagerError):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for {field}='{value}': {reason}")

class AuthenticationError(VPNManagerError):
    """Raised when authentication fails."""
    pass

class AuthorizationError(VPNManagerError):
    """Raised when authorization fails."""
    pass

class TokenError(VPNManagerError):
    """Raised when JWT token operations fail."""
    pass