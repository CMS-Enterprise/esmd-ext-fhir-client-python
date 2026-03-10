"""
Utility functions for EsmdFHIRClient.

This module provides common utility functions including retry logic,
circuit breaker pattern, validation helpers, and performance monitoring.
"""

import time
import functools
import logging
from typing import Callable, Any, Type, List, Optional, Dict, Union
from datetime import datetime, timedelta
import hashlib
import re

from .models import (
    RetryConfig, ValidationResult, PerformanceMetrics, 
    CircuitBreakerConfig, HTTPRequest, HTTPResponse
)
from .exceptions import (
    RetryExhaustedError, CircuitBreakerOpenError, ValidationError,
    NetworkError
)


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker is open for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.config.expected_exception as e:
                self._on_failure()
                raise e
                
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).seconds >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"


def retry_with_backoff(config: RetryConfig):
    """Decorator for retry logic with exponential backoff."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on authentication or validation errors
                    if isinstance(e, (ValidationError,)):
                        raise e
                    
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate backoff delay
                    delay = config.backoff_factor * (2 ** attempt)
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
            
            raise RetryExhaustedError(
                f"All {config.max_attempts} attempts failed for {func.__name__}",
                config.max_attempts,
                last_exception
            )
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """Performance monitoring utility."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
    
    def measure(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """Decorator for measuring operation performance."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                metric = PerformanceMetrics(
                    operation=operation,
                    start_time=datetime.now(),
                    metadata=metadata or {}
                )
                
                try:
                    result = func(*args, **kwargs)
                    metric.success = True
                    return result
                except Exception as e:
                    metric.success = False
                    metric.error_message = str(e)
                    raise e
                finally:
                    metric.end_time = datetime.now()
                    metric.duration_ms = (
                        metric.end_time - metric.start_time
                    ).total_seconds() * 1000
                    self.metrics.append(metric)
                    
            return wrapper
        return decorator
    
    def get_metrics(self, operation: Optional[str] = None) -> List[PerformanceMetrics]:
        """Get performance metrics, optionally filtered by operation."""
        if operation:
            return [m for m in self.metrics if m.operation == operation]
        return self.metrics.copy()
    
    def clear_metrics(self):
        """Clear all stored metrics."""
        self.metrics.clear()


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """Validate that required fields are present and not empty."""
    result = ValidationResult(is_valid=True)
    
    for field in required_fields:
        if field not in data:
            result.errors.append(f"Missing required field: {field}")
            result.field_errors.setdefault(field, []).append("Field is required")
        elif not data[field] or (isinstance(data[field], str) and data[field].strip() == ""):
            result.errors.append(f"Field '{field}' cannot be empty")
            result.field_errors.setdefault(field, []).append("Field cannot be empty")
    
    result.is_valid = len(result.errors) == 0
    return result


def validate_url(url: str) -> ValidationResult:
    """Validate URL format."""
    result = ValidationResult(is_valid=True)
    
    if not url:
        result.errors.append("URL cannot be empty")
        result.is_valid = False
        return result
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        result.errors.append("Invalid URL format")
        result.field_errors["url"] = ["Invalid URL format"]
        result.is_valid = False
    
    return result


def validate_file_path(file_path: str) -> ValidationResult:
    """Validate file path."""
    result = ValidationResult(is_valid=True)
    
    if not file_path:
        result.errors.append("File path cannot be empty")
        result.is_valid = False
        return result
    
    # Check for invalid characters
    invalid_chars = '<>"|?*'
    if any(char in file_path for char in invalid_chars):
        result.errors.append(f"File path contains invalid characters: {invalid_chars}")
        result.field_errors["file_path"] = ["Contains invalid characters"]
        result.is_valid = False
    
    return result


def validate_identifier(identifier: str, pattern: Optional[str] = None) -> ValidationResult:
    """Validate identifier format."""
    result = ValidationResult(is_valid=True)
    
    if not identifier:
        result.errors.append("Identifier cannot be empty")
        result.is_valid = False
        return result
    
    if pattern:
        if not re.match(pattern, identifier):
            result.errors.append(f"Identifier does not match required pattern: {pattern}")
            result.field_errors["identifier"] = ["Does not match required pattern"]
            result.is_valid = False
    
    return result


def calculate_md5_hash(data: Union[str, bytes]) -> str:
    """Calculate MD5 hash of data."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.md5(data).hexdigest()


def calculate_file_md5(file_path: str) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except IOError as e:
        raise ValidationError(f"Cannot read file for hashing: {e}", field="file_path", value=file_path)
    
    return hash_md5.hexdigest()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe usage."""
    # Remove or replace invalid characters
    invalid_chars = '<>"/\\|?*'
    sanitized = filename
    
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized


def format_duration(duration_ms: float) -> str:
    """Format duration in milliseconds to human-readable string."""
    if duration_ms < 1000:
        return f"{duration_ms:.2f}ms"
    elif duration_ms < 60000:
        return f"{duration_ms/1000:.2f}s"
    else:
        minutes = int(duration_ms // 60000)
        seconds = (duration_ms % 60000) / 1000
        return f"{minutes}m {seconds:.2f}s"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_extract(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely extract value from nested JSON using dot notation."""
    try:
        keys = path.split('.')
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result
    except (KeyError, TypeError, AttributeError):
        return default


def get_content_type(file_path: str) -> str:
    """Get content type based on file extension."""
    extension_map = {
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.csv': 'text/csv',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip'
    }
    
    # Get file extension
    ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
    return extension_map.get(f'.{ext}', 'application/octet-stream')


def is_expired(expires_at: datetime) -> bool:
    """Check if a timestamp has expired (with 5-minute buffer)."""
    buffer_time = timedelta(minutes=5)
    return datetime.now() >= (expires_at - buffer_time) 