"""
Custom exceptions for EsmdFHIRClient.

This module defines a hierarchy of custom exceptions that provide
specific error handling for different scenarios in the FHIR client.
"""

from typing import Optional, Dict, Any


class EsmdFHIRClientError(Exception):
    """Base exception for all EsmdFHIRClient errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(EsmdFHIRClientError):
    """Raised when there's an issue with configuration."""
    
    def __init__(self, message: str, missing_keys: Optional[list] = None):
        super().__init__(message)
        self.missing_keys = missing_keys or []


class AuthenticationError(EsmdFHIRClientError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, token_endpoint: Optional[str] = None):
        super().__init__(message)
        self.token_endpoint = token_endpoint


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired."""
    
    def __init__(self, message: str = "Access token has expired"):
        super().__init__(message)


class ValidationError(EsmdFHIRClientError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message)
        self.field = field
        self.value = value


class FileOperationError(EsmdFHIRClientError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation


class NetworkError(EsmdFHIRClientError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, url: Optional[str] = None, method: Optional[str] = None):
        super().__init__(message)
        self.url = url
        self.method = method


class FHIRServerError(EsmdFHIRClientError):
    """Raised when FHIR server returns an error."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        response_text: Optional[str] = None,
        url: Optional[str] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.url = url


class BundleSubmissionError(FHIRServerError):
    """Raised when bundle submission fails."""
    
    def __init__(
        self, 
        message: str, 
        bundle_id: Optional[str] = None,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None
    ):
        super().__init__(message, status_code, response_text)
        self.bundle_id = bundle_id


class DocumentProcessingError(EsmdFHIRClientError):
    """Raised when document processing fails."""
    
    def __init__(self, message: str, document_id: Optional[str] = None):
        super().__init__(message)
        self.document_id = document_id


class BinaryFileError(FileOperationError):
    """Raised when binary file operations fail."""
    
    def __init__(self, message: str, binary_id: Optional[str] = None, file_path: Optional[str] = None):
        super().__init__(message, file_path, "binary_download")
        self.binary_id = binary_id


class PresignedUrlError(FHIRServerError):
    """Raised when presigned URL generation fails."""
    
    def __init__(self, message: str, file_paths: Optional[list] = None):
        super().__init__(message)
        self.file_paths = file_paths or []


class PractitionerError(EsmdFHIRClientError):
    """Raised when practitioner operations fail."""
    
    def __init__(self, message: str, practitioner_id: Optional[str] = None):
        super().__init__(message)
        self.practitioner_id = practitioner_id


class SchedulerError(EsmdFHIRClientError):
    """Raised when scheduler operations fail."""
    
    def __init__(self, message: str, scheduler_type: Optional[str] = None):
        super().__init__(message)
        self.scheduler_type = scheduler_type


class NotificationError(EsmdFHIRClientError):
    """Raised when notification operations fail."""
    
    def __init__(self, message: str, notification_id: Optional[str] = None):
        super().__init__(message)
        self.notification_id = notification_id


class RetryExhaustedError(EsmdFHIRClientError):
    """Raised when retry attempts are exhausted."""
    
    def __init__(self, message: str, attempts: int, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class CircuitBreakerOpenError(EsmdFHIRClientError):
    """Raised when circuit breaker is open."""
    
    def __init__(self, message: str = "Circuit breaker is open", service: Optional[str] = None):
        super().__init__(message)
        self.service = service 