"""
Centralized application configuration management.
Provides type-safe configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str = "/etc/owpanel/database.db"
    pool_size: int = 10
    timeout: int = 30
    check_same_thread: bool = False

@dataclass
class SecurityConfig:
    """Security configuration settings."""
    secret_key: Optional[str] = None
    api_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    bcrypt_rounds: int = 12
    session_timeout: int = 3600

@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    threads: int = 4
    max_connections: int = 100

@dataclass
class CacheConfig:
    """Cache configuration settings."""
    enabled: bool = True
    default_ttl: int = 300
    max_size: int = 1000
    cleanup_interval: int = 60

@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    enabled: bool = True
    interval: int = 30
    log_level: str = "INFO"
    metrics_enabled: bool = True

@dataclass
class AppConfig:
    """Main application configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'AppConfig':
        """Load configuration from environment variables."""
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
        
        return cls(
            database=DatabaseConfig(
                path=os.getenv("DATABASE_PATH", "/etc/owpanel/database.db"),
                pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
                timeout=int(os.getenv("DB_TIMEOUT", "30")),
                check_same_thread=os.getenv("DB_CHECK_SAME_THREAD", "false").lower() == "true"
            ),
            security=SecurityConfig(
                secret_key=os.getenv("SECRET_KEY"),
                api_key=os.getenv("OPENVPN_API_KEY"),
                jwt_secret=os.getenv("JWT_SECRET"),
                bcrypt_rounds=int(os.getenv("BCRYPT_ROUNDS", "12")),
                session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600"))
            ),
            server=ServerConfig(
                host=os.getenv("SERVER_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "5000")),
                debug=os.getenv("DEBUG", "false").lower() == "true",
                threads=int(os.getenv("SERVER_THREADS", "4")),
                max_connections=int(os.getenv("MAX_CONNECTIONS", "100"))
            ),
            cache=CacheConfig(
                enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                default_ttl=int(os.getenv("CACHE_TTL", "300")),
                max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
                cleanup_interval=int(os.getenv("CACHE_CLEANUP_INTERVAL", "60"))
            ),
            monitoring=MonitoringConfig(
                enabled=os.getenv("MONITORING_ENABLED", "true").lower() == "true",
                interval=int(os.getenv("MONITORING_INTERVAL", "30")),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true"
            )
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.security.secret_key:
            raise ValueError("SECRET_KEY is required")
        if not self.security.api_key:
            raise ValueError("OPENVPN_API_KEY is required")
        if not self.security.jwt_secret:
            raise ValueError("JWT_SECRET is required")
        
        # Ensure database directory exists
        db_path = Path(self.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

# Global configuration instance
_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        env_file = "/etc/owpanel/.env"
        _config = AppConfig.from_env(env_file)
        _config.validate()
    return _config

def set_config(config: AppConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
