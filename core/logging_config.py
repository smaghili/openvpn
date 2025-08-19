"""
Structured logging configuration for the VPN Manager application.
Provides consistent logging across all components.
"""

import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import structlog
from config.app_config import get_config

def setup_structured_logging(log_level: Optional[str] = None) -> None:
    """Setup structured logging configuration."""
    config = get_config()
    level = log_level or config.monitoring.log_level
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

class LoggerMixin:
    """Mixin to add logging capabilities to classes."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)

def log_function_call(func):
    """Decorator to log function calls with parameters."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(
            "Function called",
            function=func.__name__,
            args=args[1:] if args else [],  # Skip self
            kwargs=kwargs
        )
        try:
            result = func(*args, **kwargs)
            logger.info(
                "Function completed",
                function=func.__name__,
                success=True
            )
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    return wrapper

def log_performance(func):
    """Decorator to log function performance."""
    import time
    
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                "Function performance",
                function=func.__name__,
                execution_time_ms=execution_time * 1000,
                success=True
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Function performance",
                function=func.__name__,
                execution_time_ms=execution_time * 1000,
                error=str(e),
                success=False
            )
            raise
    return wrapper
