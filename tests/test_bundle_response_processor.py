"""
Unit tests for FhirResponseProcessor in bundlesubmissionclient module.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from bundlesubmissionclient.EsmdFhirBundleSubmissionResponseProcessor import FhirResponseProcessor


class TestFhirResponseProcessor:
    """Test cases for FhirResponseProcessor class."""
    
    @pytest.fixture
    def sample_bundle_success(self):
        """Sample successful Bundle response."""
        return {
            "resourceType": "Bundle",
            "id": "response-bundle",
            "type": "transaction-response",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [
                                            {"code": "SUCCESSFUL_CREATE"}
                                        ]
                                    },
                                    "diagnostics": "Resource created successfully"
                                }
                            ]
                        }
                    }
                },
                {
                    "response": {
                        "status": "201 Created",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [
                                            {"code": "SUCCESSFUL_CREATE"}
                                        ]
                                    },
                                    "diagnostics": "Resource created successfully"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    
    @pytest.fixture
    def sample_bundle_with_errors(self):
        """Sample Bundle response with errors."""
        return {
            "resourceType": "Bundle",
            "id": "error-bundle",
            "type": "transaction-response", 
            "entry": [
                {
                    "response": {
                        "status": "400 Bad Request",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [
                                            {"code": "VALIDATION_ERROR"}
                                        ]
                                    },
                                    "diagnostics": "Invalid resource format"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    
    @pytest.fixture
    def sample_operation_outcome_success(self):
        """Sample successful OperationOutcome."""
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "details": {
                        "coding": [
                            {"code": "SUCCESSFUL_CREATE"}
                        ]
                    },
                    "diagnostics": "Operation completed successfully"
                }
            ]
        }
    
    @pytest.fixture
    def sample_operation_outcome_error(self):
        """Sample OperationOutcome with errors."""
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "details": {
                        "coding": [
                            {"code": "VALIDATION_ERROR"}
                        ]
                    },
                    "diagnostics": "Validation failed for resource"
                }
            ]
        }
    
    @pytest.fixture
    def sample_bundle_with_transaction_id(self):
        """Sample Bundle with transaction ID."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "List",
                        "extension": [
                            {
                                "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-Ext-TransactionId",
                                "valueString": "TXN123456789"
                            }
                        ]
                    }
                }
            ]
        }
    
    def test_init(self):
        """Test FhirResponseProcessor initialization."""
        response_data = {"resourceType": "Bundle"}
        processor = FhirResponseProcessor(response_data)
        
        assert processor.response_data == response_data
        assert processor.logger is not None
        assert isinstance(processor.logger, logging.Logger)
    
    def test_process_response_bundle_success(self, sample_bundle_success):
        """Test processing successful Bundle response."""
        processor = FhirResponseProcessor(sample_bundle_success)
        
        result = processor.process_response()
        
        assert result["valid"] is True
        assert "details" in result
        assert len(result["details"]) == 2  # Two successful entries
        
        for detail in result["details"]:
            assert detail["status"] == "success"
            assert "Resource created successfully" in detail["message"]
    
    def test_process_response_bundle_with_errors(self, sample_bundle_with_errors):
        """Test processing Bundle response with errors."""
        processor = FhirResponseProcessor(sample_bundle_with_errors)
        
        result = processor.process_response()
        
        assert result["valid"] is False
        assert "details" in result
        assert len(result["details"]) >= 1
        
        # Should have failure details
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert len(failure_details) >= 1
    
    def test_process_response_operation_outcome_success(self, sample_operation_outcome_success):
        """Test processing successful OperationOutcome."""
        processor = FhirResponseProcessor(sample_operation_outcome_success)
        
        result = processor.process_response()
        
        assert result["valid"] is True
        assert "details" in result
        assert len(result["details"]) == 1
        assert result["details"][0]["status"] == "success"
    
    def test_process_response_operation_outcome_error(self, sample_operation_outcome_error):
        """Test processing OperationOutcome with errors."""
        processor = FhirResponseProcessor(sample_operation_outcome_error)
        
        result = processor.process_response()
        
        assert result["valid"] is False
        assert "details" in result
        
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert len(failure_details) >= 1
    
    def test_process_response_unknown_resource_type(self):
        """Test processing response with unknown resourceType."""
        unknown_response = {"resourceType": "UnknownType"}
        processor = FhirResponseProcessor(unknown_response)
        
        result = processor.process_response()
        
        assert result["valid"] is False
        assert "Unknown resourceType: UnknownType" in result["message"]
    
    def test_process_response_missing_resource_type(self):
        """Test processing response without resourceType."""
        response_without_type = {"id": "test"}
        processor = FhirResponseProcessor(response_without_type)
        
        result = processor.process_response()
        
        assert result["valid"] is False
        assert "Unknown resourceType:" in result["message"]
    
    def test_process_response_exception_handling(self):
        """Test processing response with malformed data causing exceptions."""
        malformed_response = {"resourceType": "Bundle", "entry": "not_a_list"}
        processor = FhirResponseProcessor(malformed_response)
        
        result = processor.process_response()
        
        assert result["valid"] is False
        assert "message" in result
    
    def test_process_bundle_no_entry(self):
        """Test processing Bundle without entry field."""
        bundle_no_entry = {"resourceType": "Bundle", "id": "test"}
        processor = FhirResponseProcessor(bundle_no_entry)
        
        result = processor._process_bundle(bundle_no_entry)
        
        assert result["valid"] is False
        assert "Bundle does not contain 'entry'" in result["message"]
    
    def test_process_bundle_empty_entry(self):
        """Test processing Bundle with empty entry list."""
        bundle_empty_entry = {"resourceType": "Bundle", "entry": []}
        processor = FhirResponseProcessor(bundle_empty_entry)
        
        result = processor._process_bundle(bundle_empty_entry)
        
        assert result["valid"] is True
        assert result["details"] == []
    
    def test_process_bundle_missing_response(self):
        """Test processing Bundle entry without response field."""
        bundle_missing_response = {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient"}}]
        }
        processor = FhirResponseProcessor(bundle_missing_response)
        
        result = processor._process_bundle(bundle_missing_response)
        
        assert result["valid"] is False
        assert len(result["details"]) >= 1
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert len(failure_details) >= 1
    
    def test_process_bundle_invalid_status(self):
        """Test processing Bundle entry with invalid status."""
        bundle_invalid_status = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "response": {
                        "status": "400 Bad Request",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": []
                        }
                    }
                }
            ]
        }
        processor = FhirResponseProcessor(bundle_invalid_status)
        
        result = processor._process_bundle(bundle_invalid_status)
        
        assert result["valid"] is False
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert any("201 Created" in d["message"] for d in failure_details)
    
    def test_process_bundle_no_operation_outcome(self):
        """Test processing Bundle entry without OperationOutcome."""
        bundle_no_outcome = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "outcome": {"resourceType": "Patient"}
                    }
                }
            ]
        }
        processor = FhirResponseProcessor(bundle_no_outcome)
        
        result = processor._process_bundle(bundle_no_outcome)
        
        assert result["valid"] is False
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert any("Expected an OperationOutcome" in d["message"] for d in failure_details)
    
    def test_process_operation_outcome_no_issue(self):
        """Test processing OperationOutcome without issue field."""
        outcome_no_issue = {"resourceType": "OperationOutcome"}
        processor = FhirResponseProcessor(outcome_no_issue)
        
        result = processor._process_operation_outcome(outcome_no_issue)
        
        assert result["valid"] is False
        assert "OperationOutcome does not contain 'issue'" in result["message"]
    
    def test_process_operation_outcome_empty_issue(self):
        """Test processing OperationOutcome with empty issue list."""
        outcome_empty_issue = {"resourceType": "OperationOutcome", "issue": []}
        processor = FhirResponseProcessor(outcome_empty_issue)
        
        result = processor._process_operation_outcome(outcome_empty_issue)
        
        assert result["valid"] is True
        assert result["details"] == []
    
    def test_process_operation_outcome_missing_coding(self):
        """Test processing OperationOutcome with missing coding."""
        outcome_missing_coding = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "details": {},
                    "diagnostics": "Test diagnostic"
                }
            ]
        }
        processor = FhirResponseProcessor(outcome_missing_coding)
        
        result = processor._process_operation_outcome(outcome_missing_coding)
        
        assert result["valid"] is False
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        assert len(failure_details) >= 1
    
    def test_extract_esmd_transaction_id_from_bundle(self, sample_bundle_with_transaction_id):
        """Test extracting transaction ID from Bundle."""
        processor = FhirResponseProcessor(sample_bundle_with_transaction_id)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id == "TXN123456789"
    
    def test_extract_esmd_transaction_id_from_operation_outcome(self):
        """Test extracting transaction ID from OperationOutcome."""
        outcome_with_txn_id = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "diagnostics": "Operation successful. Esmd-TransactionId: TXN987654321 completed."
                }
            ]
        }
        processor = FhirResponseProcessor(outcome_with_txn_id)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id == "TXN987654321"
    
    def test_extract_esmd_transaction_id_not_found_bundle(self):
        """Test extracting transaction ID when not found in Bundle."""
        bundle_no_txn_id = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "List",
                        "extension": []
                    }
                }
            ]
        }
        processor = FhirResponseProcessor(bundle_no_txn_id)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id is None
    
    def test_extract_esmd_transaction_id_not_found_operation_outcome(self):
        """Test extracting transaction ID when not found in OperationOutcome."""
        outcome_no_txn_id = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "diagnostics": "Operation completed without transaction ID"
                }
            ]
        }
        processor = FhirResponseProcessor(outcome_no_txn_id)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id is None
    
    def test_extract_esmd_transaction_id_unknown_resource_type(self):
        """Test extracting transaction ID from unknown resource type."""
        unknown_resource = {"resourceType": "Patient"}
        processor = FhirResponseProcessor(unknown_resource)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id is None
    
    def test_extract_esmd_transaction_id_exception_handling(self):
        """Test transaction ID extraction with malformed data."""
        malformed_data = {"resourceType": "Bundle", "entry": "not_a_list"}
        processor = FhirResponseProcessor(malformed_data)
        
        transaction_id = processor.extract_esmd_transaction_id()
        
        assert transaction_id is None
    
    def test_log_failure_helper(self):
        """Test the _log_failure helper method."""
        processor = FhirResponseProcessor({})
        validation_results = {"valid": True, "details": []}
        
        processor._log_failure(validation_results, "Test failure message")
        
        assert validation_results["valid"] is False
        assert len(validation_results["details"]) == 1
        assert validation_results["details"][0]["status"] == "failure"
        assert validation_results["details"][0]["message"] == "Test failure message"
    
    def test_mixed_success_and_failure_bundle(self):
        """Test processing Bundle with mixed success and failure entries."""
        mixed_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [{"code": "SUCCESSFUL_CREATE"}]
                                    },
                                    "diagnostics": "Success"
                                }
                            ]
                        }
                    }
                },
                {
                    "response": {
                        "status": "400 Bad Request",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [{"code": "VALIDATION_ERROR"}]
                                    },
                                    "diagnostics": "Error"
                                }
                            ]
                        }
                    }
                }
            ]
        }
        processor = FhirResponseProcessor(mixed_bundle)
        
        result = processor.process_response()
        
        assert result["valid"] is False  # Should be false due to one failure
        assert len(result["details"]) >= 2
        
        success_details = [d for d in result["details"] if d["status"] == "success"]
        failure_details = [d for d in result["details"] if d["status"] == "failure"]
        
        assert len(success_details) >= 1
        assert len(failure_details) >= 1


@pytest.mark.integration
class TestFhirResponseProcessorIntegration:
    """Integration tests for FhirResponseProcessor."""
    
    def test_real_world_bundle_processing(self):
        """Test processing a realistic Bundle response."""
        realistic_bundle = {
            "resourceType": "Bundle",
            "id": "real-response-bundle",
            "type": "transaction-response",
            "timestamp": "2023-12-01T10:30:45-05:00",
            "entry": [
                {
                    "response": {
                        "status": "201 Created",
                        "location": "List/12345",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "severity": "information",
                                    "code": "informational",
                                    "details": {
                                        "coding": [
                                            {
                                                "system": "http://example.com/codes",
                                                "code": "SUCCESSFUL_CREATE"
                                            }
                                        ]
                                    },
                                    "diagnostics": "List resource created successfully with ID: 12345"
                                }
                            ]
                        }
                    }
                },
                {
                    "response": {
                        "status": "201 Created",
                        "location": "DocumentReference/67890",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "severity": "information",
                                    "code": "informational",
                                    "details": {
                                        "coding": [
                                            {
                                                "system": "http://example.com/codes",
                                                "code": "SUCCESSFUL_CREATE"
                                            }
                                        ]
                                    },
                                    "diagnostics": "DocumentReference created successfully with ID: 67890"
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        processor = FhirResponseProcessor(realistic_bundle)
        result = processor.process_response()
        
        assert result["valid"] is True
        assert len(result["details"]) == 2
        
        for detail in result["details"]:
            assert detail["status"] == "success"
            assert "created successfully" in detail["message"]
    
    def test_complete_workflow_with_transaction_id(self):
        """Test complete workflow including transaction ID extraction."""
        complete_response = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "List",
                        "id": "submission-list",
                        "extension": [
                            {
                                "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-Ext-TransactionId",
                                "valueString": "INTEGRATION-TXN-12345"
                            }
                        ]
                    },
                    "response": {
                        "status": "201 Created",
                        "outcome": {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "details": {
                                        "coding": [{"code": "SUCCESSFUL_CREATE"}]
                                    },
                                    "diagnostics": "Integration test successful"
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        processor = FhirResponseProcessor(complete_response)
        
        # Test processing
        process_result = processor.process_response()
        assert process_result["valid"] is True
        
        # Test transaction ID extraction
        transaction_id = processor.extract_esmd_transaction_id()
        assert transaction_id == "INTEGRATION-TXN-12345" 