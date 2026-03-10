"""
Data models for EsmdFHIRClient.

This module defines data classes used throughout the application
for type safety and structured data handling.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class HTTPMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class BundleType(Enum):
    """FHIR Bundle types."""
    TRANSACTION = "transaction"
    BATCH = "batch"
    DOCUMENT = "document"
    MESSAGE = "message"
    COLLECTION = "collection"


class ResourceType(Enum):
    """FHIR Resource types."""
    BUNDLE = "Bundle"
    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    DOCUMENT_REFERENCE = "DocumentReference"
    BINARY = "Binary"
    OPERATION_OUTCOME = "OperationOutcome"
    LIST = "List"


@dataclass
class AuthConfig:
    """Authentication configuration."""
    client_id: str
    client_secret: str
    token_endpoint: str
    scope: Optional[str] = None
    timeout: int = 30


@dataclass
class TokenInfo:
    """Token information."""
    access_token: str
    token_type: str
    expires_at: datetime
    scope: Optional[str] = None
    refresh_token: Optional[str] = None


@dataclass
class FHIRServerConfig:
    """FHIR server configuration."""
    base_url: str
    timeout: int = 30
    verify_ssl: bool = True
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    backoff_factor: float = 1.0
    retry_statuses: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    timeout: int = 30


@dataclass
class HTTPRequest:
    """HTTP request configuration."""
    method: HTTPMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Optional[Union[str, bytes, Dict[str, Any]]] = None
    timeout: int = 30
    verify_ssl: bool = True


@dataclass
class HTTPResponse:
    """HTTP response information."""
    status_code: int
    text: str
    headers: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    elapsed_seconds: Optional[float] = None


@dataclass
class FileUploadInfo:
    """File upload information."""
    file_path: str
    presigned_url: str
    md5_hash: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None


@dataclass
class PresignedUrlRequest:
    """Request for presigned URLs."""
    file_paths: List[str]
    expiration_minutes: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PresignedUrlResponse:
    """Response for presigned URLs."""
    urls: List[FileUploadInfo]
    transaction_id: Optional[str] = None
    expiration: Optional[datetime] = None


@dataclass
class BundleSubmissionRequest:
    """Bundle submission request."""
    bundle_type: BundleType
    resources: List[Dict[str, Any]]
    transaction_id: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class BundleSubmissionResponse:
    """Bundle submission response."""
    transaction_id: str
    status: str
    bundle_id: Optional[str] = None
    operation_outcome: Optional[Dict[str, Any]] = None
    response_bundle: Optional[Dict[str, Any]] = None


@dataclass
class PractitionerSearchCriteria:
    """Practitioner search criteria."""
    identifier: Optional[str] = None
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    active: Optional[bool] = None




@dataclass
class PractitionerMetadata:
    # FHIR Practitioner resource elements
    # practitioner_id: str
    # identifier: str
    family_name: str
    given_name: List[str]
    npi: str
    action_requested: str
    service_code: str
    active: bool = True
    provider_number: Optional[str] = None
    provider_taxid: Optional[str] = None    
    service_start_date: Optional[str] = None
    service_end_date: Optional[str] = None
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    telecom: List[Dict[str, str]] = field(default_factory=list)
    qualification: List[Dict[str, str]] = field(default_factory=list)
    address: List[Dict[str, str]] = field(default_factory=list)  # Added address element
    



@dataclass
class DocumentSearchCriteria:
    """Document reference search criteria."""
    patient_id: Optional[str] = None
    category: Optional[str] = None
    type_code: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    author: Optional[str] = None


@dataclass
class DocumentReferenceInfo:
    """Document reference information."""
    document_id: str
    patient_id: str
    status: str
    category: str
    type_code: str
    created: datetime
    author: Optional[str] = None
    description: Optional[str] = None
    content: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BinaryFileInfo:
    """Binary file information."""
    binary_id: str
    content_type: str
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation_date: Optional[datetime] = None


@dataclass
class NotificationCriteria:
    """Notification search criteria."""
    list_id: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    subject: Optional[str] = None


@dataclass
class TransactionNotification:
    """Transaction notification information."""
    notification_id: str
    list_id: str
    status: str
    subject: str
    created: datetime
    updated: Optional[datetime] = None
    entries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LoggerConfig:
    """Logger configuration."""
    name: str
    level: str = "INFO"
    format_string: Optional[str] = None
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_logging: bool = True


@dataclass
class OperationOutcome:
    """FHIR OperationOutcome information."""
    severity: str
    code: str
    details: Optional[str] = None
    diagnostics: Optional[str] = None
    location: Optional[List[str]] = None
    expression: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Validation result."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_errors: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict) 


@dataclass
class ProviderDeliveryAckMetadata:
    transaction_id: str
    organization_id: str
    npi: str
    delivery_datetime: datetime
    severity: Optional[str] = None
    code: Optional[str] = None   
    diagnostics: Optional[str] = None
