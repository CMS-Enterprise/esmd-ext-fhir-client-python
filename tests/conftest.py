"""
Shared pytest fixtures and configuration for EsmdFHIRClient tests.
"""

import shutil
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_content = """
server:
  base_url: "http://test-server:9012/fhir"
  presigned_base_url: "http://test-server:9016/fhir"
  timeout: 30

auth:
  token_endpoint: "https://test.example.com/auth/token"
  client_id: "test_client_id"
  client_secret: "test_client_secret"
  scope: "test_scope"

logging:
  level: "DEBUG"
  log_file: "test.log"

org:
  oid: "urn:oid:1.2.3.4.5"
  name: "Test Organization"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_config():
    """Create a mock ConfigUtility for testing."""
    config = Mock(spec=ConfigUtility)
    config.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
    config.get_presigned_url_base.return_value = "http://test-server:9016/fhir"
    config.get_timeout.return_value = 30
    config.get_token_endpoint.return_value = "https://test.example.com/auth/token"
    config.get_client_id.return_value = "test_client_id"
    config.get_client_secret.return_value = "test_client_secret"
    config.get_scope.return_value = "test_scope"
    config.get_oid.return_value = "urn:oid:1.2.3.4.5"
    config.get_org_name.return_value = "Test Organization"
    config.get_logging_level.return_value = "DEBUG"
    config.get_log_file.return_value = "test.log"
    config.validate_required_config.return_value = True
    return config


@pytest.fixture
def mock_auth_client():
    """Create a mock EsmdAuthClient for testing."""
    auth_client = Mock(spec=EsmdAuthClient)
    auth_client.get_token.return_value = "test_access_token"
    auth_client.get_auth_header.return_value = {"Authorization": "Bearer test_access_token"}
    auth_client.token = "test_access_token"
    auth_client.token_type = "Bearer"
    auth_client.expires_in = 3600
    return auth_client


@pytest.fixture
def sample_file_paths(tmp_path,project_root):
    # """Create sample test files for testing file operations."""
    # files = []
    # for i in range(2):
    #     file_path = tmp_path / f"test_document_{i}.pdf"
    #     file_path.write_bytes(b"Sample PDF content for testing")
    #     files.append(str(file_path))
    # return files
    """Copy sample test files from a local directory to a temporary directory."""
    # Your local directory containing the sample test files
    # Get project root (two levels up from this test file, adjust as needed)
    

    # Folder in project root containing test files
    source_dir = project_root / "tests" / "sample_files"
    print("Source dir:", source_dir)
    print("Files found:", list(source_dir.glob("*.xml")))
    files = []
    for i, file in enumerate(source_dir.glob("*.xml")):
        dest_file = tmp_path / f"test_document_{i}.xml"
        shutil.copy(file, dest_file)
        files.append(str(dest_file))
    print("Copied files:", files)
    return files

@pytest.fixture
def project_root():
    """Return the absolute path to the project root directory."""
    # This assumes your tests are in a 'tests' folder inside the project root
    return Path(__file__).parent.parent.resolve()

@pytest.fixture
def sample_extensions_data():
    """Provide sample extensions data for testing."""
    return {
            "OrganizationId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId",
            "OrganizationIdValue": "urn:oid:123.456.657.126",
            "IntendedRecipient": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient",
            "IntendedRecipientValue": "urn:oid:2.16.840.1.113883.13.34.110.1.999.1",
            "LinesOfBusinessId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId",
            "LinesOfBusinessIdValue": "1",
            "ClaimId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ClaimId",
            "ClaimIdValue": "CLAIM1234567",
            "CaseId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-CaseId",
            "CaseIdValue": "CASE1234567",
            "SplitNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-SplitNumber",
            "SplitNumberValue": "1-5",
            "AttachmentControlNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-AttachmentControlNumber",
            "AttachmentControlNumberValue": "CONTROL123",
            "ResponseTypeCategory": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ResponseTypeCategory",
            "ResponseTypeCategoryValue": "RESPONSE_TYPE",
            "UniqueId" : "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-UniqueId",
            "UniqueIdValue": "UNIQUE1234567",
            "NPI": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
            "NPIValue": "1234567890"
    }


@pytest.fixture
def sample_identifiers_data():
    """Provide sample identifiers data for testing."""
    return {
        "UniqueIdSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Idn-UniqueId",
        "UniqueIdValue": "UNIQUE1234569",
        "ParentUniqueIdSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
        "ParentUniqueIdValue": "1234567890"
    }


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session for testing HTTP calls."""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = '{"status": "success"}'
        mock_response.raise_for_status.return_value = None
        
        mock_session.post.return_value = mock_response
        mock_session.get.return_value = mock_response
        mock_session.put.return_value = mock_response
        
        yield mock_session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env_vars = {
        'ESMD_CLIENT_ID': '6kk4kfak4ktk7d3gnu0l584lec',
        'ESMD_CLIENT_SECRET': '1apm85jm5pdo5mlaks79f6vlq8d92v5fde2mt3a52tel2g975slt',
        'ESMD_TOKEN_ENDPOINT': 'https://dev.cpiapigateway.cms.gov/api/esmdp/auth/generate',
        'ESMD_FHIR_SERVER_URL': 'https://dev.cpiapigateway.cms.gov/api/esmdf/v1/fhir',
        'ESMD_LOG_LEVEL': 'INFO'
    }
    
    # Store original values
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers and skipping."""
    # Skip slow tests by default unless --runslow is given
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    # Skip network tests unless --runnetwork is given
    if not config.getoption("--runnetwork"):
        skip_network = pytest.mark.skip(reason="need --runnetwork option to run")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--runnetwork", action="store_true", default=False, help="run network tests"
    )
    parser.addoption(
        "--runintegration", action="store_true", default=False, help="run integration tests"
    ) 