# EsmdFHIRClient - Enhanced FHIR Client Library

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-green.svg)](https://github.com/your-repo/EsmdFHIRClient)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/your-repo/EsmdFHIRClient)

A comprehensive, production-ready Python client library for interacting with esMD FHIR services. This enhanced version includes robust error handling, retry logic, circuit breaker patterns, comprehensive validation, and extensive testing.

## 🚀 Key Features

### Core Functionality
- **Bundle Submission**: Submit FHIR bundles with presigned URL support
- **Practitioner Management**: Search, create, and manage practitioner resources
- **Document Reference Handling**: Upload and manage document references
- **Notification Processing**: Handle transaction notifications and lists

### Enhanced Features ✨
- **🔒 Robust Authentication**: OAuth2 with token caching and automatic refresh
- **🛡️ Error Handling**: Comprehensive exception hierarchy with detailed error context
- **🔄 Retry Logic**: Exponential backoff with configurable retry policies
- **⚡ Circuit Breaker**: Fault tolerance with automatic recovery
- **📊 Performance Monitoring**: Built-in metrics and performance tracking
- **✅ Input Validation**: Comprehensive validation for all inputs
- **🎯 Type Safety**: Full type hints throughout the codebase
- **📝 Comprehensive Logging**: Structured logging with configurable levels and audit trails
- **🔍 Audit Trails**: Detailed audit logging for authentication and operations
- **🧪 Extensive Testing**: 95%+ test coverage with unit and integration tests
- **📦 Modular Design**: Import only the modules you need for your use case

## 📦 Installation

### Production Installation
```bash
pip install esmd-fhir-client
```

### Development Installation
```bash
git clone https://github.com/your-repo/EsmdFHIRClient.git
cd EsmdFHIRClient
pip install -e ".[dev]"
```

### Optional Dependencies
```bash
# For enhanced performance monitoring
pip install "esmd-fhir-client[monitoring]"

# For development tools
pip install "esmd-fhir-client[dev]"

# For all features
pip install "esmd-fhir-client[all]"
```

## ⚙️ Configuration

### Environment Variables with .env File (Recommended)

The library supports loading configuration from a `.env` file for easier management. Create a `.env` file in your project root:

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual values
nano .env
```

#### .env File Structure
```bash
# Authentication (Required)
ESMD_CLIENT_ID=your-client-id
ESMD_CLIENT_SECRET=your-client-secret
ESMD_TOKEN_ENDPOINT=https://your-auth-server/token

# Server Configuration (Required)
ESMD_FHIR_SERVER_URL=https://your-fhir-server/fhir
ESMD_PRESIGNED_URL_BASE=https://your-fhir-server/fhir

# Optional Configuration
ESMD_SCOPE=read write
ESMD_TIMEOUT=30
ESMD_VERIFY_SSL=true

# Organization Details
ESMD_ORG_OID=urn:oid:1.2.3.4
ESMD_ORG_NAME=Your Organization

# Logging
ESMD_LOG_LEVEL=INFO
ESMD_LOG_FILE=/var/log/esmd-client.log
ESMD_CONSOLE_LOGGING=true

# Advanced Configuration
ESMD_RETRY_MAX_ATTEMPTS=3
ESMD_RETRY_BACKOFF_FACTOR=1.0
ESMD_CIRCUIT_BREAKER_ENABLED=true
ESMD_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
ESMD_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

### Environment Variables (Alternative)
You can also set environment variables directly:

```bash
# Authentication (Required)
export ESMD_CLIENT_ID="your-client-id"
export ESMD_CLIENT_SECRET="your-client-secret"
export ESMD_TOKEN_ENDPOINT="https://your-auth-server/token"

# Server Configuration (Required)
export ESMD_FHIR_SERVER_URL="https://your-fhir-server/fhir"
export ESMD_PRESIGNED_URL_BASE="https://your-fhir-server/fhir"

# Optional Configuration
export ESMD_SCOPE="read write"
export ESMD_TIMEOUT="30"
export ESMD_VERIFY_SSL="true"

# Organization Details
export ESMD_ORG_OID="urn:oid:1.2.3.4"
export ESMD_ORG_NAME="Your Organization"

# Logging
export ESMD_LOG_LEVEL="INFO"
export ESMD_LOG_FILE="/var/log/esmd-client.log"
export ESMD_CONSOLE_LOGGING="true"
```

### Configuration File (config.yaml) - Optional
```yaml
# Server Configuration
server:
  base_url: "https://your-fhir-server/fhir"
  presigned_base_url: "https://your-fhir-server/fhir"
  timeout: 30
  verify_ssl: true
  headers:
    User-Agent: "EsmdFHIRClient/2.0"

# Authentication
auth:
  token_endpoint: "https://your-auth-server/token"
  client_id: "your-client-id"
  client_secret: "your-secret"  # Use environment variable instead
  scope: "read write"

# Organization
org:
  oid: "urn:oid:1.2.3.4"
  name: "Your Organization"

# Logging
logging:
  level: "INFO"
  log_file: "/var/log/esmd-client.log"
  console: true
```

**Note**: The library now prioritizes environment variables and `.env` files over YAML configuration files. The YAML file is optional and mainly used for advanced configuration scenarios.

### Configuration Priority Order
The library follows this priority order for configuration values:
1. **System environment variables** (highest priority)
2. **`.env` file variables** (if `load_env=True`)
3. **YAML config file** (if exists)
4. **Default values** (lowest priority)

### Configuration Features
- **Environment Variable Support**: All settings can be configured via environment variables
- **`.env` File Loading**: Automatic loading of `.env` files for easier development
- **YAML Configuration**: Optional YAML files for advanced configuration scenarios
- **Validation**: Comprehensive validation of configuration values
- **Caching**: Performance optimization with configuration caching
- **Auto-discovery**: Automatic discovery of configuration files

## 🏃‍♂️ Quick Start

### Modular Library Usage

The library is designed to be modular - you can import only the components you need:

```python
# Import only what you need
from esmd_shared import EsmdAuthClient, ConfigUtility, setup_logger
from bundlesubmissionclient import PresignedUrlGenerator
from practitionerclient import PractitionerRequestSubmitter
from documentrefscheduler import DocumentReferenceScheduler
from notificationscheduler import NotificationScheduler
```

### Basic Bundle Submission
```python
from esmd_shared import ConfigUtility, EsmdAuthClient
from bundlesubmissionclient.PresignedUrlGenerator import PresignedUrlGenerator
from bundlesubmissionclient.PrepareEsmdBundleSubmissionData import PrepareBundleSubmission

# Initialize with automatic configuration (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
generator = PresignedUrlGenerator(config, auth_client)

# Prepare submission data
extensions_data = {
    "SenderOidValue": "urn:oid:1.2.840.10008.3.1.2.1.1",
    "IntendedRecipientValue": "urn:oid:2.16.840.1.113883.13.34.110.1.100.23",
    "ClaimIdValue": "CLAIM1234567"
}

identifiers_data = {
    "UniqueIdValue": "UNIQUE1234569",
    "NpiValue": "1234567890"
}

file_paths = [
    "/path/to/document1.pdf",
    "/path/to/document2.pdf"
]

# Submit bundle with automatic error handling and retries
try:
    response = generator.entry_point(
        "UNIQUE1234569", 
        extensions_data, 
        identifiers_data, 
        file_paths
    )
    print("Bundle submitted successfully!")
except Exception as e:
    print(f"Submission failed: {e}")
```

### Advanced Bundle Submission with Full Control
```python
from esmd_shared.models import PresignedUrlRequest, RetryConfig
from esmd_shared.exceptions import ValidationError, NetworkError

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=5,
    backoff_factor=2.0,
    retry_statuses=[500, 502, 503, 504, 429],
    timeout=60
)

# Initialize with custom configuration
generator = PresignedUrlGenerator(
    config_util=config,
    auth_client=auth_client,
    retry_config=retry_config
)

# Create structured request
request = PresignedUrlRequest(
    file_paths=file_paths,
    expiration_minutes=120,
    metadata={"sender_oid": "urn:oid:1.2.840.10008.3.1.2.1.1"}
)

try:
    # Generate presigned URLs with validation
    response = generator.generate_presigned_urls_structured(request)
    
    print(f"Generated {len(response.urls)} presigned URLs")
    for url_info in response.urls:
        print(f"- {url_info.file_path}: {url_info.file_size} bytes")
        
except ValidationError as e:
    print(f"Validation error: {e.message}")
    if e.field:
        print(f"Problem with field: {e.field}")
except NetworkError as e:
    print(f"Network error: {e.message}")
    print(f"URL: {e.url}, Method: {e.method}")
```

### Practitioner Management
```python
from practitionerclient.EsmdPractitionerRequestSubmitter import PractitionerRequestSubmitter
from esmd_shared.models import PractitionerSearchCriteria

# Initialize practitioner client
practitioner_client = PractitionerRequestSubmitter(config)

# Search for practitioners
search_criteria = PractitionerSearchCriteria(
    family_name="Smith",
    given_name="John",
    active=True
)

try:
    results = practitioner_client.search_practitioners(search_criteria)
    print(f"Found {len(results)} practitioners")
except Exception as e:
    print(f"Search failed: {e}")
```

### Document Reference Processing
```python
from documentrefscheduler.EsmdDocumentRefLettersPullScheduler import DocumentReferenceScheduler
from esmd_shared.models import DocumentSearchCriteria

# Initialize scheduler
scheduler = DocumentReferenceScheduler(config)

# Search for document references
search_criteria = DocumentSearchCriteria(
    patient_id="patient-123",
    category="clinical-note",
    status="current"
)

try:
    documents = scheduler.search_documents(search_criteria)
    print(f"Found {len(documents)} documents")
except Exception as e:
    print(f"Document search failed: {e}")
```

### Enhanced Logging and Monitoring
```python
from esmd_shared import setup_logger, PerformanceMonitor, LoggerConfig

# Setup enhanced logging with audit trails
logger_config = LoggerConfig(
    name="my_app",
    level="DEBUG",
    file_path="/var/log/my_app.log",
    max_bytes=50*1024*1024,  # 50MB
    backup_count=10,
    console_logging=True
)

logger = setup_logger("my_app", config=logger_config, enhanced=True)

# Use context-aware logging with audit trails
logger.set_context(user_id="123", operation="bundle_submit")
logger.info("Starting bundle submission")

# Performance monitoring
monitor = PerformanceMonitor()

@monitor.measure("file_processing")
def process_files(files):
    # Your file processing logic
    pass

# Get performance metrics
metrics = monitor.get_metrics("file_processing")
for metric in metrics:
    print(f"Operation: {metric.operation}, Duration: {metric.duration_ms}ms")
```

## 📦 Modular Library Usage

### Bundle Submission Module
```python
from esmd_shared import EsmdAuthClient, ConfigUtility
from bundlesubmissionclient import PresignedUrlGenerator, PresignedUrlUploader

# Initialize with shared components (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
generator = PresignedUrlGenerator(config, auth_client)
uploader = PresignedUrlUploader(config, auth_client)
```

### Practitioner Management Module
```python
from esmd_shared import EsmdAuthClient, ConfigUtility
from practitionerclient import PractitionerRequestSubmitter

# Initialize practitioner client (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
practitioner_client = PractitionerRequestSubmitter()
```

### Document Reference Module
```python
from esmd_shared import EsmdAuthClient, ConfigUtility
from documentrefscheduler import DocumentReferenceScheduler

# Initialize document scheduler (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
doc_scheduler = DocumentReferenceScheduler()
```

### Notification Processing Module
```python
from esmd_shared import EsmdAuthClient, ConfigUtility
from notificationscheduler import NotificationScheduler

# Initialize notification scheduler (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
notification_scheduler = NotificationScheduler()
```

### Provider Delivery Ack Module
```python
from esmd_shared import EsmdAuthClient, ConfigUtility
from providerdeliveryack.ProviderDeliveryAckMetadata import ProviderDeliveryAckMetadataHandler 
from esmd_shared.models import ProviderDeliveryAckMetadata, OperationOutcome

# Initialize practitioner client (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
metadata = ProviderDeliveryAckMetadataHandler(metadata)
provider_ack_client = submit_provider_delivery_ack(fhir_list) 

```

### Shared Utilities Only
```python
from esmd_shared import (
    EsmdAuthClient, ConfigUtility, setup_logger,
    validate_required_fields, retry_with_backoff,
    PerformanceMonitor, CircuitBreaker
)

# Use shared utilities in your own code (loads from .env file)
config = ConfigUtility()  # Automatically loads .env file
auth_client = EsmdAuthClient(config_util=config)
logger = setup_logger("my_app")

# Validate inputs
validation = validate_required_fields(data, required_fields)

# Use retry logic
@retry_with_backoff(max_attempts=3)
def my_function():
    pass
```

## 🏗️ Architecture

### Project Structure
```
EsmdFHIRClient/
├── esmd_shared/                    # Shared utilities and core functionality
│   ├── __init__.py
│   ├── auth.py                     # Enhanced authentication client
│   ├── config.py                   # Centralized configuration management
│   ├── logger.py                   # Advanced logging utilities
│   ├── models.py                   # Data models and type definitions
│   ├── exceptions.py               # Custom exception hierarchy
│   ├── utils.py                    # Utility functions and decorators
│   └── http_client.py              # Enhanced HTTP client
├── bundlesubmissionclient/         # Bundle submission functionality
│   ├── PresignedUrlGenerator.py   # Enhanced with validation & retry
│   ├── PresignedUrlUploader.py    # Enhanced with progress tracking
│   ├── PrepareEsmdBundleSubmissionData.py  # Enhanced with validation
│   ├── EsmdBundleSubmission.py    # Enhanced with retry logic
│   └── EsmdFhirBundleSubmissionResponseProcessor.py  # Enhanced parsing
├── practitionerclient/             # Practitioner management
├── documentrefscheduler/           # Document reference handling
├── notificationscheduler/          # Notification processing
├── providerdeliveryack/            # Provider Delivery Ack Submission
├── tests/                          # Comprehensive test suite
│   ├── test_shared_*.py           # Shared utility tests
│   ├── test_bundle_*.py           # Bundle submission tests
│   ├── test_practitioner_*.py     # Practitioner tests
│   ├── test_notification_scheduler.py  # Notifications retrieval tests
│   ├── test_document_retrieval_scheduler.py   # Document retrieval tests
│   ├── test_provider_delivery_ack.py     # Provider Delivery Ack tests
│   └── conftest.py                # Shared test fixtures
├── config.yaml.template           # Configuration template (optional)
├── .env.example                   # Environment variables template
├── requirements.txt               # Production dependencies
├── setup.py                       # Package configuration
├── pytest.ini                     # Test configuration
├── mypy.ini                       # Type checking configuration
├── Makefile                       # Development commands
└── README.md                      # This file
```

### Key Components

#### Shared Utilities (`esmd_shared/`)
- **Authentication**: OAuth2 with token caching, retry logic, and automatic refresh
- **Configuration**: Centralized configuration with environment variables, `.env` files, and YAML support
- **Logging**: Structured logging with rotation, filtering, and context management
- **HTTP Client**: Connection pooling, retry logic, circuit breaker, and performance monitoring
- **Error Handling**: Comprehensive exception hierarchy with detailed context
- **Validation**: Input validation, type checking, and data sanitization

#### Bundle Submission (`bundlesubmissionclient/`)
- **Presigned URL Generation**: Enhanced with validation and structured data models
- **File Upload**: Progress tracking, integrity checking, and error recovery
- **Bundle Preparation**: FHIR bundle creation with validation and metadata
- **Submission**: Robust submission with retry logic and response processing

#### Practitioner Management (`practitionerclient/`)
- **Search**: Advanced search with filtering and pagination
- **CRUD Operations**: Create, read, update, delete with validation
- **Metadata Handling**: Comprehensive practitioner metadata management

#### Document Processing (`documentrefscheduler/`)
- **Document Search**: Flexible search with multiple criteria
- **Binary Handling**: File download and processing
- **Scheduling**: Automated document processing workflows

#### Notification Handling (`notificationscheduler/`)
- **List Processing**: Transaction notification list handling
- **Status Tracking**: Notification status monitoring and updates
- **Scheduling**: Automated notification processing

#### Provider Delivery Ack Submission (`providerdeliveryack/`)
- **List Preparation**: Creates a FHIR List resource with valid metadata and performs validation.
- **Submission and Response Processing**: Submits the request to esMD and processes the response.


## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not network"          # Skip network tests

# Run tests for specific module
pytest tests/test_shared_auth.py
pytest tests/test_bundle_*.py
```

### Test Categories
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: End-to-end tests with real dependencies
- **Network Tests**: Tests requiring network connectivity
- **Slow Tests**: Performance and stress tests

### Writing Tests
```python
import pytest
from esmd_shared.auth import EsmdAuthClient
from esmd_shared.exceptions import AuthenticationError

class TestEsmdAuthClient:
    def test_successful_authentication(self, mock_auth_config):
        client = EsmdAuthClient(config_util=mock_auth_config)
        token = client.get_token()
        assert token is not None
        assert len(token) > 0
    
    def test_authentication_failure(self, mock_invalid_config):
        client = EsmdAuthClient(config_util=mock_invalid_config)
        with pytest.raises(AuthenticationError):
            client.get_token()
```

## 🔧 Development

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/your-repo/EsmdFHIRClient.git
cd EsmdFHIRClient

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Set up configuration (recommended approach)
cp .env.example .env
# Edit .env file with your actual configuration values
nano .env

# Optional: Set up YAML configuration for advanced scenarios
cp config.yaml.template config.yaml
# Edit config.yaml if needed for advanced configuration
```

### Building Individual Modules
```bash
# Build all modules (recommended)
make build-all

# Build specific modules (shared module included automatically)
make build-bundle        # Bundle submission module
make build-practitioner  # Practitioner module
make build-document      # Document scheduler module
make build-notification  # Notification scheduler module

# Or use the build script directly
python build_modules.py                    # Build all modules
python build_modules.py bundlesubmissionclient  # Build specific module
```

### Development Commands
```bash
# Code quality checks
make lint                         # Run linting
make format                       # Format code
make type-check                   # Type checking
make security-check               # Security analysis

# Testing
make test                         # Run tests
make test-coverage               # Test with coverage
make test-integration            # Integration tests

# Building
make build                       # Build package
make clean                       # Clean build artifacts

# Documentation
make docs                        # Generate documentation
make docs-serve                  # Serve documentation locally
```

### Code Quality Standards
- **Type Hints**: All public methods must have type hints
- **Documentation**: All modules, classes, and methods must be documented
- **Error Handling**: Use custom exceptions with detailed context
- **Testing**: Minimum 90% test coverage for new code
- **Validation**: Validate all inputs and handle edge cases
- **Logging**: Use structured logging with appropriate levels

## 🚨 Error Handling

### Exception Hierarchy
```python
EsmdFHIRClientError                 # Base exception
├── ConfigurationError             # Configuration issues
├── AuthenticationError            # Authentication failures
│   └── TokenExpiredError         # Token expiration
├── ValidationError                # Input validation failures
├── NetworkError                   # Network-related errors
├── FileOperationError            # File system errors
├── FHIRServerError               # FHIR server errors
│   ├── BundleSubmissionError     # Bundle submission failures
│   └── PresignedUrlError         # Presigned URL generation failures
├── RetryExhaustedError           # All retries failed
└── CircuitBreakerOpenError       # Circuit breaker protection
```

### Error Handling Best Practices
```python
from esmd_shared.exceptions import EsmdFHIRClientError, ValidationError

try:
    # Your operation
    result = client.submit_bundle(bundle_data)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field: {e.field}, Value: {e.value}")
except NetworkError as e:
    print(f"Network error: {e.message}")
    print(f"URL: {e.url}, Method: {e.method}")
except EsmdFHIRClientError as e:
    print(f"Client error: {e.message}")
    if e.details:
        print(f"Details: {e.details}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 📊 Performance Monitoring

### Built-in Metrics
```python
from esmd_shared import PerformanceMonitor

# Monitor function performance
monitor = PerformanceMonitor()

@monitor.measure("bundle_submission")
def submit_bundle(bundle):
    # Your implementation
    pass

# Get performance metrics
metrics = monitor.get_metrics("bundle_submission")
for metric in metrics:
    print(f"Duration: {metric.duration_ms}ms, Success: {metric.success}")
```

## 🔍 Audit Logging

### Authentication Audit Trails
The library provides comprehensive audit logging for authentication operations:

```python
from esmd_shared import EsmdAuthClient, ConfigUtility

config = ConfigUtility()
auth_client = EsmdAuthClient(config_util=config)

# This will generate audit logs like:
# [AUDIT] Initiating token request to https://auth.example.com/token
# [AUDIT] Client ID: 12345678... (truncated)
# [AUDIT] Scope: read write
# [AUDIT] Token retrieved successfully. Expires at 2024-01-01 12:00:00
# [AUDIT] Token type: Bearer
# [AUDIT] Token scope: read write

token = auth_client.get_token()
```

### Custom Audit Logging
```python
from esmd_shared import setup_logger

logger = setup_logger("audit_logger", level="INFO")

# Log audit events
logger.info("[AUDIT] User login attempt: user_id=12345")
logger.info("[AUDIT] Bundle submission: bundle_id=ABC123, files=3")
logger.info("[AUDIT] Document access: doc_id=DOC456, user_id=12345")
```

### HTTP Client Statistics
```python
from esmd_shared.http_client import EnhancedHTTPClient

client = EnhancedHTTPClient(server_config)

# Make requests...

# Get statistics
stats = client.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Error rate: {stats['error_rate']:.2%}")
print(f"Circuit breaker state: {stats['circuit_breaker_state']}")
```

## 🔐 Security

### Authentication Security
- OAuth2 client credentials flow
- Automatic token refresh
- Secure token storage (memory only)
- Configurable token expiration handling

### Configuration Security
- Environment variable precedence
- Sensitive data warnings
- SSL/TLS verification (configurable)
- Input sanitization and validation

### Network Security
- Connection pooling with limits
- Request/response size limits
- Timeout protection
- Circuit breaker protection

## 🔄 Migration Guide

### From Previous Version
If you're upgrading from a previous version, see [CHANGELOG.md](CHANGELOG.md) for detailed migration instructions.

### Key Changes in v2.0.0
1. **Eliminated Code Duplication**: Removed duplicate `EsmdAuthClient.py` files across modules
2. **Unified Authentication**: All modules now use the enhanced `esmd_shared.auth.EsmdAuthClient`
3. **Modular Imports**: Simplified imports using the shared module structure
4. **Enhanced Audit Logging**: Added comprehensive audit trails for authentication operations
5. **Better Standards**: Improved code organization and reduced redundancy
6. **Environment File Support**: Added automatic loading of `.env` files for configuration
7. **Centralized Configuration**: Removed duplicate `config_util.py` and `config.yaml` files, unified under `esmd_shared/config.py`
8. **Centralized Logging**: Removed duplicate `logger.py` files, unified under `esmd_shared/logger.py`
9. **Automatic Shared Module Inclusion**: Build system automatically includes shared module dependencies

### Migration Steps
1. **Update Imports**: Change from local to shared imports:
   ```python
   # Old (v1.x)
   from EsmdAuthClient import EsmdAuthClient
   from config_util import ConfigUtility
   from logger import setup_logger
   
   # New (v2.0+)
   from esmd_shared import EsmdAuthClient, ConfigUtility, setup_logger
   ```

2. **Update Constructor Calls**:
   ```python
   # Old
   auth_client = EsmdAuthClient()
   
   # New
   config = ConfigUtility()
   auth_client = EsmdAuthClient(config_util=config)
   ```

3. **Configuration**: Create `.env` file or use environment variables (YAML config is optional)
4. **Error Handling**: Update exception handling to use new hierarchy
5. **Type Hints**: Add type hints if extending the library

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all quality checks pass
5. Submit a pull request

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Type hints are present
- [ ] Documentation is updated
- [ ] Error handling is comprehensive
- [ ] Performance impact is considered

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
- **Documentation**: [Full documentation](https://your-docs-site.com)
- **Issues**: [GitHub Issues](https://github.com/your-repo/EsmdFHIRClient/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/EsmdFHIRClient/discussions)

### Troubleshooting

#### Common Issues

**Authentication Failures**
```bash
# Check your credentials
python -c "from esmd_shared.config import ConfigUtility; c=ConfigUtility(); print('✓' if c.validate_configuration().is_valid else '✗')"

# Test token endpoint
curl -X POST "$ESMD_TOKEN_ENDPOINT" \
  -H "clientid: $ESMD_CLIENT_ID" \
  -H "clientsecret: $ESMD_CLIENT_SECRET"
```

**Configuration Issues**
```bash
# Validate configuration
python -c "
from esmd_shared.config import ConfigUtility
config = ConfigUtility()
result = config.validate_configuration()
print('✓ Valid' if result.is_valid else f'✗ Errors: {result.errors}')
"
```

**Network Issues**
```bash
# Test connectivity
python -c "
from esmd_shared.http_client import EnhancedHTTPClient
from esmd_shared.models import FHIRServerConfig
config = FHIRServerConfig(base_url='$ESMD_FHIR_SERVER_URL')
client = EnhancedHTTPClient(config)
try:
    response = client.get(config.base_url + '/metadata')
    print(f'✓ Connected: {response.status_code}')
except Exception as e:
    print(f'✗ Failed: {e}')
"
```

### Performance Tuning

#### Configuration Options
```python
# Optimize for high throughput
retry_config = RetryConfig(
    max_attempts=2,        # Fewer retries
    backoff_factor=0.5,    # Faster backoff
    timeout=10             # Shorter timeouts
)

# Optimize for reliability
retry_config = RetryConfig(
    max_attempts=5,        # More retries
    backoff_factor=2.0,    # Exponential backoff
    timeout=60             # Longer timeouts
)
```

#### Connection Pooling
```python
# High-performance configuration
from requests.adapters import HTTPAdapter

adapter = HTTPAdapter(
    pool_connections=20,    # More connections
    pool_maxsize=50,       # Larger pool
    max_retries=3
)
```

---

**EsmdFHIRClient** - Production-ready FHIR client with enterprise-grade reliability and performance. 