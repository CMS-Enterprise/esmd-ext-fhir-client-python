"""
Unit tests for all practitioner modules in practitionerclient.
"""

import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from practitionerclient.EsmdPractitionerRequestSubmitter import PractitionerRequestSubmitter
from practitionerclient.EsmdPractitionerResponse import FhirBatchResponseProcessor
from practitionerclient.PractitionerMetadata import PractitionerMetadata


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
    
#     def test_init(self, submitter, mock_dependencies):
#         """Test PractitionerRequestSubmitter initialization."""
#         assert submitter.base_url == "http://test-server:9012/fhir"
#         assert submitter.config_util is not None
#         assert submitter.auth_client is not None
    
#     @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.put')
#     def test_submit_practitioner_success(self, mock_put, submitter, sample_practitioner_data):
#         """Test successful practitioner submission."""
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 201
#         mock_response.json.return_value = {
#             "resourceType": "Practitioner",
#             "id": "created-practitioner-001"
#         }
#         mock_put.return_value = mock_response
        
#         result = submitter.submit_practitioner(sample_practitioner_data)
        
#         assert result is not None
#         assert result["id"] == "created-practitioner-001"
        
#         # Verify request
#         mock_put.assert_called_once()
#         call_args = mock_put.call_args
#         assert "Practitioner" in call_args[0][0]
#         assert call_args[1]['headers']['Authorization'] == 'Bearer test_access_token'
#         assert call_args[1]['headers']['Content-Type'] == 'application/fhir+json'
    
#     def test_submit_practitioner_no_token(self, submitter, sample_practitioner_data, caplog):
#         """Test practitioner submission without token."""
#         submitter.auth_client.get_token.return_value = None
        
#         result = submitter.submit_practitioner(sample_practitioner_data)
        
#         assert result is None
#         assert "No access token could be retrieved" in caplog.text
    
#     @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.post')
#     def test_submit_practitioner_http_error(self, mock_post, submitter, sample_practitioner_data, caplog):
#         """Test practitioner submission with HTTP error."""
#         caplog.set_level('ERROR', logger=submitter.logger.name)
#         mock_response = Mock()
#         mock_response.status_code = 400
#         mock_response.text = "Bad Request"
#         mock_post.return_value = mock_response
        
#         result = submitter.submit_practitioner(sample_practitioner_data)
        
#         assert result is None
#         assert "Error " in caplog.text
    
#     @patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.post')
#     def test_submit_batch_practitioners(self, mock_post, submitter):
#         """Test batch practitioner submission."""
#         batch_data = {
#             "resourceType": "Bundle",
#             "type": "batch",
#             "entry": [
#                 {
#                     "resource": {
#                         "resourceType": "Practitioner",
#                         "id": "practitioner-001"
#                     },
#                     "request": {
#                         "method": "POST",
#                         "url": "Practitioner"
#                     }
#                 },
#                 {
#                     "resource": {
#                         "resourceType": "Practitioner", 
#                         "id": "practitioner-002"
#                     },
#                     "request": {
#                         "method": "POST",
#                         "url": "Practitioner"
#                     }
#                 }
#             ]
#         }
        
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "resourceType": "Bundle",
#             "type": "batch-response"
#         }
#         mock_post.return_value = mock_response
        
#         result = submitter.submit_practitioner_bundle(batch_data)
        
#         assert result is not None
#         assert result["type"] == "batch-response"


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
    
#     def test_init(self, sample_batch_response_success):
#         """Test FhirBatchResponseProcessor initialization."""
#         processor = FhirBatchResponseProcessor(sample_batch_response_success)        
        
#         assert processor.bundle_response == sample_batch_response_success
#         assert processor.logger is not None
    
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
        
        result = processor.process_response()
        
        print(f"result, {result}")
        assert result["valid"] is False  # Has failures
        assert result["total_entries"] == 2
        assert result["successful_entries"] == 1
        assert result["failed_entries"] == 1
    
#     def test_process_response_invalid_bundle(self):
#         """Test processing invalid bundle."""
#         invalid_bundle = {"resourceType": "Patient"}  # Not a Bundle
#         processor = FhirBatchResponseProcessor(invalid_bundle)
        
#         result = processor.process_response()
        
#         assert result["valid"] is False
#         assert "Not a valid Bundle" in result["message"]
    
#     def test_process_response_no_entries(self):
#         """Test processing bundle without entries."""
#         empty_bundle = {
#             "resourceType": "Bundle",
#             "type": "batch-response"
#         }
#         processor = FhirBatchResponseProcessor(empty_bundle)
        
#         result = processor.process_response()
        
#         assert result["valid"] is True
#         assert result["total_entries"] == 0
    
#     def test_extract_successful_practitioners(self, sample_batch_response_success):
#         """Test extracting successful practitioners."""
#         processor = FhirBatchResponseProcessor(sample_batch_response_success)
        
#         practitioners = processor.extract_successful_practitioners()
        
#         assert len(practitioners) == 2
#         assert practitioners[0]["id"] == "123"
#         assert practitioners[1]["id"] == "456"
    
#     def test_extract_failed_operations(self, sample_batch_response_mixed):
#         """Test extracting failed operations."""
#         processor = FhirBatchResponseProcessor(sample_batch_response_mixed)
        
#         failures = processor.extract_failed_operations()
        
#         assert len(failures) == 1
#         assert failures[0]["status"] == "400 Bad Request"
#         assert "Invalid practitioner data" in failures[0]["diagnostics"]
    
#     def test_get_summary_statistics(self, sample_batch_response_mixed):
#         """Test getting summary statistics."""
#         processor = FhirBatchResponseProcessor(sample_batch_response_mixed)
        
#         stats = processor.get_summary_statistics()
        
#         assert stats["total"] == 2
#         assert stats["successful"] == 1
#         assert stats["failed"] == 1
#         assert stats["success_rate"] == 50.0


# class TestPractitionerMetadata:
#     """Test cases for PractitionerMetadata class."""
    
#     @pytest.fixture
#     def sample_practitioner_data(self):
#         """Sample practitioner data."""
#         return {
#             "resourceType": "Practitioner",
#             "id": "practitioner-001",
#             "identifier": [
#                 {
#                     "system": "http://hl7.org/fhir/sid/us-npi",
#                     "value": "1234567890"
#                 }
#             ],
#             "name": [
#                 {
#                     "family": "Smith",
#                     "given": ["John", "Michael"],
#                     "prefix": ["Dr."],
#                     "suffix": ["MD"]
#                 }
#             ],
#             "gender": "male",
#             "birthDate": "1980-01-15",
#             "qualification": [
#                 {
#                     "code": {
#                         "coding": [
#                             {
#                                 "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
#                                 "code": "MD",
#                                 "display": "Doctor of Medicine"
#                             }
#                         ]
#                     }
#                 }
#             ]
#         }
    
#     def test_init(self, sample_practitioner_data):
#         """Test PractitionerMetadata initialization."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         assert metadata.practitioner_data == sample_practitioner_data
#         assert metadata.logger is not None
    
#     def test_get_npi_number(self, sample_practitioner_data):
#         """Test extracting NPI number."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         npi = metadata.get_npi_number()
        
#         assert npi == "1234567890"
    
#     def test_get_npi_number_not_found(self):
#         """Test NPI extraction when not found."""
#         data_without_npi = {
#             "resourceType": "Practitioner",
#             "identifier": [
#                 {
#                     "system": "http://other.system",
#                     "value": "OTHER123"
#                 }
#             ]
#         }
#         metadata = PractitionerMetadata(data_without_npi)
        
#         npi = metadata.get_npi_number()
        
#         assert npi is None
    
#     def test_get_full_name(self, sample_practitioner_data):
#         """Test getting full name."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         full_name = metadata.get_full_name()
        
#         assert "Dr." in full_name
#         assert "John" in full_name
#         assert "Michael" in full_name
#         assert "Smith" in full_name
#         assert "MD" in full_name
    
#     def test_get_gender(self, sample_practitioner_data):
#         """Test getting gender."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         gender = metadata.get_gender()
        
#         assert gender == "male"
    
#     def test_get_birth_date(self, sample_practitioner_data):
#         """Test getting birth date."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         birth_date = metadata.get_birth_date()
        
#         assert birth_date == "1980-01-15"
    
#     def test_get_qualifications(self, sample_practitioner_data):
#         """Test getting qualifications."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         qualifications = metadata.get_qualifications()
        
#         assert len(qualifications) == 1
#         assert qualifications[0]["code"] == "MD"
#         assert qualifications[0]["display"] == "Doctor of Medicine"
    
#     def test_validate_required_fields(self, sample_practitioner_data):
#         """Test validation of required fields."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         is_valid, missing_fields = metadata.validate_required_fields()
        
#         assert is_valid is True
#         assert len(missing_fields) == 0
    
#     def test_validate_required_fields_missing(self):
#         """Test validation with missing required fields."""
#         incomplete_data = {
#             "resourceType": "Practitioner"
#             # Missing identifier, name
#         }
#         metadata = PractitionerMetadata(incomplete_data)
        
#         is_valid, missing_fields = metadata.validate_required_fields()
        
#         assert is_valid is False
#         assert "identifier" in missing_fields
#         assert "name" in missing_fields
    
#     def test_get_formatted_summary(self, sample_practitioner_data):
#         """Test getting formatted summary."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         summary = metadata.get_formatted_summary()
        
#         assert "NPI" in summary
#         assert "1234567890" in summary
#         assert "Dr. John Michael Smith MD" in summary
#         assert "male" in summary
#         assert "1980-01-15" in summary
    
#     def test_to_dict(self, sample_practitioner_data):
#         """Test converting to dictionary."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         result_dict = metadata.to_dict()
        
#         assert result_dict["npi"] == "1234567890"
#         assert result_dict["full_name"] == "Dr. John Michael Smith MD"
#         assert result_dict["gender"] == "male"
#         assert result_dict["birth_date"] == "1980-01-15"
#         assert len(result_dict["qualifications"]) == 1
    
#     def test_compare_practitioners(self, sample_practitioner_data):
#         """Test comparing practitioners."""
#         metadata1 = PractitionerMetadata(sample_practitioner_data)
        
#         # Create slightly different practitioner
#         different_data = sample_practitioner_data.copy()
#         different_data["gender"] = "female"
#         metadata2 = PractitionerMetadata(different_data)
        
#         differences = metadata1.compare_with(metadata2)
        
#         assert "gender" in differences
#         assert differences["gender"]["self"] == "male"
#         assert differences["gender"]["other"] == "female"
    
#     def test_is_complete_profile(self, sample_practitioner_data):
#         """Test checking if profile is complete."""
#         metadata = PractitionerMetadata(sample_practitioner_data)
        
#         is_complete = metadata.is_complete_profile()
        
#         assert is_complete is True
    
#     def test_is_complete_profile_incomplete(self):
#         """Test incomplete profile check."""
#         incomplete_data = {
#             "resourceType": "Practitioner",
#             "identifier": [
#                 {
#                     "system": "http://hl7.org/fhir/sid/us-npi",
#                     "value": "1234567890"
#                 }
#             ]
#             # Missing name, gender, birthDate
#         }
#         metadata = PractitionerMetadata(incomplete_data)
        
#         is_complete = metadata.is_complete_profile()
        
#         assert is_complete is False


# @pytest.mark.integration
# class TestPractitionerModulesIntegration:
#     """Integration tests for practitioner modules."""
    
#     def test_end_to_end_practitioner_workflow(self):
#         """Test complete practitioner workflow."""
#         # Sample practitioner data
#         practitioner_data = {
#             "resourceType": "Practitioner",
#             "identifier": [
#                 {
#                     "system": "http://hl7.org/fhir/sid/us-npi",
#                     "value": "9876543210"
#                 }
#             ],
#             "name": [
#                 {
#                     "family": "Johnson",
#                     "given": ["Jane"],
#                     "prefix": ["Dr."]
#                 }
#             ],
#             "gender": "female"
#         }
        
#         # Test metadata extraction
#         metadata = PractitionerMetadata(practitioner_data)
#         assert metadata.get_npi_number() == "9876543210"
#         assert "Dr. Jane Johnson" in metadata.get_full_name()
        
#         # Test validation
#         is_valid, missing = metadata.validate_required_fields()
#         assert is_valid is True
        
#         # Mock submission test
#         with patch('practitionerclient.EsmdPractitionerRequestSubmitter.requests.post') as mock_post:
#             mock_response = Mock()
#             mock_response.status_code = 201
#             mock_response.json.return_value = {
#                 "resourceType": "Practitioner",
#                 "id": "created-123"
#             }
#             mock_post.return_value = mock_response
            
#             submitter = PractitionerRequestSubmitter()
#             result = submitter.submit_practitioner(practitioner_data)
            
#             assert result["id"] == "created-123"
    
#     def test_batch_processing_workflow(self):
#         """Test batch processing workflow."""
#         # Create batch response
#         batch_response = {
#             "resourceType": "Bundle",
#             "type": "batch-response",
#             "entry": [
#                 {
#                     "response": {
#                         "status": "201 Created",
#                         "location": "Practitioner/batch-001"
#                     },
#                     "resource": {
#                         "resourceType": "Practitioner",
#                         "id": "batch-001",
#                         "identifier": [
#                             {
#                                 "system": "http://hl7.org/fhir/sid/us-npi",
#                                 "value": "1111111111"
#                             }
#                         ]
#                     }
#                 }
#             ]
#         }
        
#         # Process response
#         processor = FhirBatchResponseProcessor(batch_response)
#         result = processor.process_response()
        
#         assert result["valid"] is True
#         assert result["successful_entries"] == 1
        
#         # Extract successful practitioners
#         practitioners = processor.extract_successful_practitioners()
#         assert len(practitioners) == 1
        
#         # Analyze metadata
#         for practitioner in practitioners:
#             metadata = PractitionerMetadata(practitioner)
#             assert metadata.get_npi_number() == "1111111111" 