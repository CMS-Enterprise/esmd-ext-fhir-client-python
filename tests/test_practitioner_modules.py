"""
Unit tests for all practitioner modules in practitionerclient.
"""

from unittest import result
import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from practitionerclient.EsmdPractitionerRequestSubmitter import PractitionerRequestSubmitter
from practitionerclient.EsmdPractitionerResponse import FhirBatchResponseProcessor
from practitionerclient.PractitionerMetadata import PractitionerMetadata
from practitionerclient.PractitionerMetadata import PreparePractitionerAndBundlePractitioner

class TestPractitionerRequestSubmitter:
    """Test cases for PractitionerRequestSubmitter class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('practitionerclient.EsmdPractitionerRequestSubmitter.ConfigUtility') as mock_config, \
             patch('practitionerclient.EsmdPractitionerRequestSubmitter.EsmdAuthClient') as mock_auth:
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                #'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }
    
    @pytest.fixture
    def submitter(self, mock_dependencies):
        """Create PractitionerRequestSubmitter instance."""
        return PractitionerRequestSubmitter()
    
    @pytest.fixture
    def sample_practitioner_data(self):
        """Sample practitioner data for testing."""
        return {
            "resourceType": "Practitioner",
            "id": "practitioner-001",
            "identifier": [
                {
                    "system": "http://hl7.org/fhir/sid/us-npi",
                    "value": "1234567890"
                }
            ],
            "name": [
                {
                    "family": "Smith",
                    "given": ["John", "Michael"],
                    "prefix": ["Dr."]
                }
            ],
            "gender": "male",
            "birthDate": "1980-01-15"
        }
    
    def test_init(self, submitter, mock_dependencies):
        """Test PractitionerRequestSubmitter initialization."""
        assert submitter.base_url == "http://test-server:9012/fhir"
        assert submitter.config_util is not None
        assert submitter.auth_client is not None
    
    @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.put')
    def test_submit_practitioner_success(self, mock_put, submitter, sample_practitioner_data):
        """Test successful practitioner submission."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "resourceType": "Practitioner",
            "id": "created-practitioner-001"
        }
        mock_put.return_value = mock_response
        
        result = submitter.submit_practitioner(sample_practitioner_data)
        
        assert result is not None
        assert result["id"] == "created-practitioner-001"
        
        # Verify request
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert "Practitioner" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer test_access_token'
        assert call_args[1]['headers']['Content-Type'] == 'application/fhir+json'
    
    def test_submit_practitioner_no_token(self, submitter, sample_practitioner_data, caplog):
        """Test practitioner submission without token."""
        submitter.auth_client.get_token.return_value = None
        
        result = submitter.submit_practitioner(sample_practitioner_data)
        
        assert result is None
        assert "No access token could be retrieved" in caplog.text
    
    @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.post')
    def test_submit_practitioner_http_error(self, mock_post, submitter, sample_practitioner_data, caplog):
        """Test practitioner submission with HTTP error."""
        caplog.set_level('ERROR', logger=submitter.logger.name)
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        result = submitter.submit_practitioner(sample_practitioner_data)
        
        assert result is None
        assert "Error " in caplog.text
    
    @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.post')
    def test_submit_batch_practitioners(self, mock_post, submitter):
        """Test batch practitioner submission."""
        batch_data = {
            "resourceType": "Bundle",
            "type": "batch",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "practitioner-001"
                    },
                    "request": {
                        "method": "POST",
                        "url": "Practitioner"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Practitioner", 
                        "id": "practitioner-002"
                    },
                    "request": {
                        "method": "POST",
                        "url": "Practitioner"
                    }
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "type": "batch-response"
        }
        mock_post.return_value = mock_response
        
        result = submitter.submit_practitioner_bundle(batch_data)
        
        assert result is not None
        assert result["type"] == "batch-response"


class TestFhirBatchResponseProcessor:
    """Test cases for FhirBatchResponseProcessor class."""
    
    @pytest.fixture
    def sample_batch_response_success(self):
        """Sample successful batch response."""
        return {
            "resourceType": "Bundle",
            "type": "batch-response",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "location": "Practitioner/123"
                    },
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "123"
                    }
                },
                {
                    "response": {
                        "status": "201 Created",
                        "location": "Practitioner/456"
                    },
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "456"
                    }
                }
            ]
        }
    
    @pytest.fixture
    def sample_batch_response_mixed(self):
        """Sample batch response with mixed results."""
        return {
            "resourceType": "Bundle",
            "type": "batch-response",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "location": "Practitioner/123"
                    }
                },
                {
                    "response": {
                        "status": "400 Bad Request"
                    },
                    "resource": {
                        "resourceType": "OperationOutcome",
                        "issue": [
                            {
                                "severity": "error",
                                "code": "invalid",
                                "diagnostics": "Invalid practitioner data"
                            }
                        ]
                    }
                }
            ]
        }
    
    def test_init(self, sample_batch_response_success):
        """Test FhirBatchResponseProcessor initialization."""
        processor = FhirBatchResponseProcessor(sample_batch_response_success)        
        
        assert processor.bundle_response == sample_batch_response_success
        assert processor.logger is not None
    
    def test_process_response_success(self, sample_batch_response_success):
        """Test processing successful batch response."""
        processor = FhirBatchResponseProcessor(sample_batch_response_success)
        
        result = processor.extract_practitioner_ids_with_status()
        
        print(f"result, {result}")
        
        assert result is not None
        assert len(result) == 2
    
    def test_process_response_mixed_results(self, sample_batch_response_mixed):
        """Test processing batch response with mixed results."""
        processor = FhirBatchResponseProcessor(sample_batch_response_mixed)
        
        result = processor.extract_practitioner_ids_with_status()
        
        print(f"result, {result}")
        
        assert len(result) == 2
        assert result[0]['status'] == '201 Created'
        assert result[1]['status'] == '400 Bad Request'
    
    def test_process_response_invalid_bundle(self, caplog):
        """Test processing invalid bundle."""
        invalid_bundle = {"resourceType": "Patient"}  # Not a Bundle
        caplog.set_level('ERROR', logger='practitionerclient.EsmdPractitionerResponse.FhirBatchResponseProcessor')
        processor = FhirBatchResponseProcessor(invalid_bundle)
        print(f"result, {processor}")
        result = processor.extract_practitioner_ids_with_status()

        assert "Missing 'resourceType' or 'entry'" in caplog.text

    def test_process_response_no_entries(self, caplog):
        """Test processing bundle without entries."""
        empty_bundle = {
            "resourceType": "Bundle",
            "type": "batch-response"
        }
        caplog.set_level('ERROR', logger='practitionerclient.EsmdPractitionerResponse.FhirBatchResponseProcessor')
        processor = FhirBatchResponseProcessor(empty_bundle)
        
        result = processor.extract_practitioner_ids_with_status()
        assert "Missing 'resourceType' or 'entry'" in caplog.text

    def test_extract_successful_practitioners(self, sample_batch_response_success):
        """Test extracting successful practitioners."""
        processor = FhirBatchResponseProcessor(sample_batch_response_success)

        practitioners = processor.extract_practitioner_ids_with_status()
        
        print(f"practitioners, {practitioners}")
        assert len(practitioners) == 2
        assert practitioners[0]["practitioner_id"] == "123"
        assert practitioners[1]["practitioner_id"] == "456"
    
    def test_extract_failed_operations(self, sample_batch_response_mixed):
        """Test extracting failed operations."""
        processor = FhirBatchResponseProcessor(sample_batch_response_mixed)
        
        failures = processor.extract_practitioner_ids_with_status()
        print(f"failures, {failures}")        
        assert failures[1]["status"] == "400 Bad Request"   


class TestPractitionerMetadata:
    """Test cases for PractitionerMetadata class."""
    
    @pytest.fixture
    def sample_practitioner_data(self):
        """Sample practitioner data shaped to match the PractitionerMetadata dataclass fields."""
        return {
            "family_name": "Smith",
            "given_name": ["John", "Michael"],
            "npi": "1234567890",
            "action_requested": "A",
            "service_code": "EEP",
            "active": True,
            "provider_number": "5432112345",
            "provider_taxid": "TAXID123",
            "service_start_date": "2024-01-01",
            "service_end_date": "2024-12-31",
            "gender": "male",
            "birthdate": "1980-01-15",
            "telecom": [
                {"system": "phone", "value": "555-123-4567", "use": "work"}
            ],
            "qualification": [
                {"code": "MD", "display": "Doctor of Medicine"}
            ],
            "address": [
                {
                    "line": ["123 Main St"],
                    "city": "Springfield",
                    "state": "IL",
                    "postalCode": "62701",
                    "country": "USA"
                }
            ]
        }
    @pytest.fixture
    def sample_practitioner_data_missing_npi(self):
        """Sample practitioner data shaped to match the PractitionerMetadata dataclass fields."""
        return {
            "family_name": "Smith",
            "given_name": ["John", "Michael"],
            "action_requested": "A",
            "service_code": "EEP",
            "active": True,
            "provider_number": "5432112345",
            "provider_taxid": "TAXID123",
            "service_start_date": "2024-01-01",
            "service_end_date": "2024-12-31",
            "gender": "male",
            "birthdate": "1980-01-15",
            "telecom": [
                {"system": "phone", "value": "555-123-4567", "use": "work"}
            ],
            "qualification": [
                {"code": "MD", "display": "Doctor of Medicine"}
            ],
            "address": [
                {
                    "line": ["123 Main St"],
                    "city": "Springfield",
                    "state": "IL",
                    "postalCode": "62701",
                    "country": "USA"
                }
            ]
        }
    
    def test_init(self, sample_practitioner_data):
        """Test PractitionerMetadata initialization."""
        # Construct dataclass using keyword unpacking of the fixture dict
        metadata = PractitionerMetadata(**sample_practitioner_data)

        # Assert key fields were set correctly on the dataclass
        assert metadata.family_name == sample_practitioner_data["family_name"]
        assert metadata.given_name == sample_practitioner_data["given_name"]
        assert metadata.npi == sample_practitioner_data["npi"]
        assert metadata.action_requested == sample_practitioner_data["action_requested"]
        assert metadata.service_code == sample_practitioner_data["service_code"]

    def test_missing_npi(self, sample_practitioner_data_missing_npi):
        """Test PractitionerMetadata initialization with missing NPI."""
        # Missing required 'npi' should raise a TypeError from the dataclass constructor
        with pytest.raises(TypeError):
            PractitionerMetadata(**sample_practitioner_data_missing_npi)


    def test_validate_required_fields_missing(self, caplog):
        """Test validation with missing required fields."""
        incomplete_data = {
            "resourceType": "Practitioner"
            # Missing identifier, name
        }
        # Constructing the dataclass with incomplete data should raise TypeError
        with pytest.raises(TypeError) as excinfo:
            PractitionerMetadata(**incomplete_data)

        # The dataclass will raise TypeError for an unexpected keyword ('resourceType')
        msg = str(excinfo.value).lower()
        print(f"msg, {msg}")
        assert "unexpected keyword" in msg or "got an unexpected keyword argument" in msg
        # message should reference the resourceType key we passed
        assert "resourcetype" in msg or "resource" in msg
        


@pytest.mark.integration
def test_integration_create_and_submit_practitioners():
    """Integration-style test: create practitioners from dataclasses, assert resource details, bundle and submit."""
    # Import the helper and dataclass from the module under test
    from practitionerclient.PractitionerMetadata import PreparePractitionerAndBundlePractitioner, PractitionerMetadata as PM

    # Create two PractitionerMetadata dataclass instances (mirror example usage)
    p1_dc = PM(
        family_name="Doe",
        given_name=["John"],
        gender="male",
        npi="1234567890",
        provider_number="5432112345",
        provider_taxid="TAXID123",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        address=[{
            "line": ["123 Main St"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "USA"
        }],
        telecom=[{"system": "phone", "value": "555-123-4567", "use": "work"}]
    )

    p2_dc = PM(
        family_name="Smith",
        given_name=["Jane"],
        gender="female",
        npi="9876543210",
        provider_number="5432112345",
        provider_taxid="TAXID987",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-02-01",
        service_end_date="2024-02-28",
        address=[{
            "line": ["456 Oak Ave"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62702",
            "country": "USA"
        }],
        telecom=[{"system": "phone", "value": "555-987-6543", "use": "work"}]
    )

    # Use the Prepare helper to create FHIR Practitioner resources
    prep1 = PreparePractitionerAndBundlePractitioner(p1_dc)
    prep2 = PreparePractitionerAndBundlePractitioner(p2_dc)

    practitioner1 = prep1.create_practitioner()
    practitioner2 = prep2.create_practitioner()

    # Basic structure assertions
    assert practitioner1["resourceType"] == "Practitioner"
    assert "id" in practitioner1 and practitioner1["id"]
    assert practitioner1["name"][0]["family"] == "Doe"
    assert practitioner1["name"][0]["given"] == ["John"]
    assert practitioner1.get("telecom") and practitioner1["telecom"][0]["value"] == "555-123-4567"

    # Extension assertions: NPI should be present as an extension
    npi_exts = [e for e in practitioner1.get("extension", []) if e.get("url", "").endswith("Esmd-Ext-NPI")]
    assert len(npi_exts) == 1
    assert npi_exts[0]["valueString"] == "1234567890"

    # Build a bundle and assert entries
    bundle = PreparePractitionerAndBundlePractitioner.create_practitioner_bundle([practitioner1, practitioner2])
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "batch"
    assert isinstance(bundle.get("entry"), list) and len(bundle["entry"]) == 2

    # Patch configuration and auth client so PractitionerRequestSubmitter can be constructed
    with patch('practitionerclient.EsmdPractitionerRequestSubmitter.ConfigUtility') as mock_config, \
         patch('practitionerclient.EsmdPractitionerRequestSubmitter.EsmdAuthClient') as mock_auth:

        mock_config_instance = Mock()
        mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
        mock_config.return_value = mock_config_instance

        mock_auth_instance = Mock()
        mock_auth_instance.get_token.return_value = "test_access_token"
        mock_auth.return_value = mock_auth_instance

        # Mock the HTTP call during submission and verify submit_practitioner uses the Practitioner id in the URL
        with patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.put') as mock_put:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"resourceType": "Practitioner", "id": practitioner1["id"]}
            mock_put.return_value = mock_response

            submitter = PractitionerRequestSubmitter()
            result = submitter.submit_practitioner(practitioner1)

            assert result is not None
            assert result["id"] == practitioner1["id"]

            # Verify the HTTP PUT call used the expected URL containing Practitioner/<id>
            mock_put.assert_called_once()
            called_url = mock_put.call_args[0][0]
            assert f"Practitioner/{practitioner1['id']}" in called_url



@pytest.mark.integration
class TestPractitionerModulesIntegration:
    """Integration tests for practitioner modules."""
    
    def test_end_to_end_practitioner_workflow(self):
        """Test complete practitioner workflow."""
        # Sample practitioner data
        practitioner_data = PractitionerMetadata(
        family_name="Doe",
        given_name=["John"],
        gender="male",
        npi="1234567890",
        provider_number="5432112345",
        provider_taxid="TAXID123",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        address=[{
            "line": ["123 Main St"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "USA"
        }],
        telecom=[{"system": "phone", "value": "555-123-4567", "use": "work"}]
    )
     # create FHIR resource using the project helper
        
        prep = PreparePractitionerAndBundlePractitioner(practitioner_data)
        practitioner_resource = prep.create_practitioner()

        # submit using the submitter (instance of PractitionerRequestSubmitter)
        submitter = PractitionerRequestSubmitter()
        print("Submitting Practitioner Request...")
        practitioner_response = submitter.submit_practitioner(practitioner_resource)
        print(f"practitioner_response: {practitioner_response}")
        
        
        if practitioner_response:
            print("Practitioner Submission Response:")
        else:
            print("Failed to submit the practitioner.")
    
    
    
    def test_batch_processing_end_to_end_workflow(self):
        """Test batch processing workflow."""
        # Create batch response
    practitioner1_dc = PractitionerMetadata(
        family_name="Doe",
        given_name=["John"],
        gender="male",
        npi="1234567890",
        provider_number="5432112345",
        provider_taxid="TAXID123",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        address=[{
            "line": ["123 Main St"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "USA"
        }],
        telecom=[{
            "system": "phone",
            "value": "555-123-4567",
            "use": "work"
        }]
    )

    practitioner2_dc = PractitionerMetadata(
        family_name="Smith",
        given_name=["Jane"],
        gender="female",
        npi="9876543210",
        provider_number="5432112345",
        provider_taxid="TAXID987",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-02-01",
        service_end_date="2024-02-28",
        address=[{
            "line": ["456 Oak Ave"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62702",
            "country": "USA"
        }],
        telecom=[{
            "system": "phone",
            "value": "555-987-6543",
            "use": "work"
        }]
    )
        
    # Use PreparePractitionerAndBundlePractitioner to create resources
    prep1 = PreparePractitionerAndBundlePractitioner(practitioner1_dc)
    prep2 = PreparePractitionerAndBundlePractitioner(practitioner2_dc)

    practitioner_metadata_1 = prep1.create_practitioner()
    practitioner_metadata_2 = prep2.create_practitioner()

    practitioners_metadata_list = [practitioner_metadata_1, practitioner_metadata_2]

    # Create Bundle Practitioner resource
    bundle_practitioner = PreparePractitionerAndBundlePractitioner.create_practitioner_bundle(practitioners_metadata_list)

    # Submit the practitioner bundle
    print("Submitting Practitioner Bundle...")
    # submit using the submitter (instance of PractitionerRequestSubmitter)
    submitter = PractitionerRequestSubmitter()
    bundle_response = submitter.submit_practitioner_bundle(bundle_practitioner)

    # Print the response
    if bundle_response:
        print("Practitioner Bundle Submission Response:")
        print(json.dumps(bundle_response, indent=2))
        processor = FhirBatchResponseProcessor(bundle_response)
        practitioner_response_list = processor.extract_practitioner_ids_with_status()
        # Print the extracted practitioner information
        print("Extracted Practitioner Information:", json.dumps(practitioner_response_list, indent=2))
    else:
        print("Failed to submit the practitioner bundle.")