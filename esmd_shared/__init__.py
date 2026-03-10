"""
EsmdFHIRClient Shared Utilities Package

This package contains common utilities shared across all EsmdFHIRClient modules
to eliminate code duplication and provide consistent functionality.
"""

__version__ = "2.0.0"
__author__ = "EsmdFHIRClient Team"

# Import main classes for easy access
from .auth import EsmdAuthClient
from .config import ConfigUtility
from .logger import setup_logger
from .models import (
    PresignedUrlRequest, PresignedUrlResponse, FileUploadInfo,
    HTTPRequest, HTTPResponse, ValidationResult, RetryConfig,
    AuthConfig, TokenInfo, CircuitBreakerConfig
)
from .exceptions import (
    EsmdFHIRClientError, ConfigurationError, AuthenticationError,
    ValidationError, NetworkError, FileOperationError, FHIRServerError
)
from .utils import (
    validate_required_fields, validate_file_path, calculate_file_md5,
    get_content_type, retry_with_backoff, sanitize_filename,
    PerformanceMonitor, CircuitBreaker
)

__all__ = [
    # Core classes
    "EsmdAuthClient",
    "ConfigUtility", 
    "setup_logger",
    
    # Models
    "PresignedUrlRequest",
    "PresignedUrlResponse", 
    "FileUploadInfo",
    "HTTPRequest",
    "HTTPResponse",
    "ValidationResult",
    "RetryConfig",
    "AuthConfig",
    "TokenInfo",
    "CircuitBreakerConfig",
    
    # Exceptions
    "EsmdFHIRClientError",
    "ConfigurationError",
    "AuthenticationError", 
    "ValidationError",
    "NetworkError",
    "FileOperationError",
    "FHIRServerError",
    
    # Utilities
    "validate_required_fields",
    "validate_file_path",
    "calculate_file_md5",
    "get_content_type",
    "retry_with_backoff",
    "sanitize_filename",
    "PerformanceMonitor",
    "CircuitBreaker"
] 