"""
Unit tests for BundleSubmission in bundlesubmissionclient module.
"""

import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock
from bundlesubmissionclient.EsmdBundleSubmission import BundleSubmission


class TestBundleSubmission:
    """Test cases for BundleSubmission class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('bundlesubmissionclient.EsmdBundleSubmission.ConfigUtility') as mock_config, \
             patch('bundlesubmissionclient.EsmdBundleSubmission.EsmdAuthClient') as mock_auth:
            
            # Set up mock returns
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
    def bundle_submission(self, mock_dependencies):
        """Create BundleSubmission instance with mocked dependencies."""
        return BundleSubmission("http://custom-server:9012/fhir")
    
    @pytest.fixture
    def sample_bundle(self):
        """Sample FHIR bundle for testing."""
        return {
            "resourceType": "Bundle",
            "id": "test-bundle-001",
            "meta": {
                "profile": ["http://test.com/StructureDefinition/Test-Bundle"]
            },
            "type": "transaction",
            "timestamp": "2023-12-01T10:30:45-05:00",
            "entry": [
                {
                    "fullUrl": "List/test-list-001",
                    "resource": {
                        "resourceType": "List",
                        "id": "test-list-001",
                        "status": "current"
                    },
                    "request": {
                        "method": "POST",
                        "url": "List"
                    }
                },
                {
                    "fullUrl": "DocumentReference/test-doc-001",
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "test-doc-001",
                        "status": "current"
                    },
                    "request": {
                        "method": "POST",
                        "url": "DocumentReference"
                    }
                }
            ]
        }
    
    def test_init_with_custom_url(self, bundle_submission, mock_dependencies):
        """Test BundleSubmission initialization with custom URL."""
        assert bundle_submission.esmd_fhir_server_url == "http://custom-server:9012/fhir"
        assert bundle_submission.base_url == "http://test-server:9012/fhir"  # From config
        assert bundle_submission.config_util is not None
        assert bundle_submission.auth_client is not None
    
    def test_init_url_assignment(self, mock_dependencies):
        """Test URL assignment during initialization."""
        bundle_submission = BundleSubmission("http://init-url:8080/fhir")
        
        # esmd_fhir_server_url should be from constructor parameter
        assert bundle_submission.esmd_fhir_server_url == "http://init-url:8080/fhir"
        # base_url should be from config utility
        assert bundle_submission.base_url == "http://test-server:9012/fhir"
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_success(self, mock_post, bundle_submission, sample_bundle):
        """Test successful bundle submission."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "id": "response-bundle",
            "type": "transaction-response",
            "entry": [
                {"response": {"status": "201 Created"}},
                {"response": {"status": "201 Created"}}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Execute submission
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        # Verify result
        assert success is True
        assert result["resourceType"] == "Bundle"
        assert result["type"] == "transaction-response"
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL (should have trailing slash)
        assert call_args[0][0] == "http://custom-server:9012/fhir/"
        
        # Check headers
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer test_access_token'
        assert headers['Content-Type'] == 'application/fhir+json'
        assert headers['Accept'] == 'application/fhir+json'
        
        
        # Check data
        sent_data = json.loads(call_args[1]['data'])
        assert sent_data == sample_bundle
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_url_trailing_slash(self, mock_post, mock_dependencies, sample_bundle):
        """Test that URL gets trailing slash if missing."""
        # Create bundle submission with URL without trailing slash
        bundle_submission = BundleSubmission("http://no-slash-server:9012/fhir")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Execute submission
        bundle_submission.submit_bundle(sample_bundle)
        
        # Verify URL has trailing slash
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://no-slash-server:9012/fhir/"
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_url_already_has_slash(self, mock_post, mock_dependencies, sample_bundle):
        """Test that URL with existing trailing slash is not modified."""
        # Create bundle submission with URL that already has trailing slash
        bundle_submission = BundleSubmission("http://has-slash-server:9012/fhir/")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Execute submission
        bundle_submission.submit_bundle(sample_bundle)
        
        # Verify URL still has single trailing slash
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://has-slash-server:9012/fhir/"
    
    def test_submit_bundle_no_token(self, bundle_submission, sample_bundle, caplog):
        """Test bundle submission when no access token available."""
        # Mock auth client to return no token
        bundle_submission.auth_client.get_token.return_value = None
        
        result = bundle_submission.submit_bundle(sample_bundle)
        
        assert result is None
        assert "No access token could be retrieved" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_http_error(self, mock_post, bundle_submission, sample_bundle, caplog):
        """Test bundle submission with HTTP error."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request - Invalid bundle format"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error")
        mock_post.return_value = mock_response
        
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        assert success is False
        assert "error" in result
        assert result["status_code"] == 400
        assert result["response"] == "Bad Request - Invalid bundle format"
        assert "HTTP error occurred" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_connection_error(self, mock_post, bundle_submission, sample_bundle, caplog):
        """Test bundle submission with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        assert success is False
        assert "error" in result
        assert "Connection refused" in result["error"]
        assert "Connection error occurred" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_timeout_error(self, mock_post, bundle_submission, sample_bundle, caplog):
        """Test bundle submission with timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        assert success is False
        assert "error" in result
        assert "Request timed out" in result["error"]
        assert "Timeout error occurred" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_request_exception(self, mock_post, bundle_submission, sample_bundle, caplog):
        """Test bundle submission with general request exception."""
        mock_post.side_effect = requests.exceptions.RequestException("General request error")
        
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        assert success is False
        assert "error" in result
        assert "General request error" in result["error"]
        assert "Request exception occurred" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_unexpected_exception(self, mock_post, bundle_submission, sample_bundle, caplog):
        """Test bundle submission with unexpected exception."""
        mock_post.side_effect = ValueError("Unexpected value error")
        
        success, result = bundle_submission.submit_bundle(sample_bundle)
        
        assert success is False
        assert "error" in result
        assert "Unexpected value error" in result["error"]
        assert "An unexpected error occurred" in caplog.text
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_server_error_status_codes(self, mock_post, bundle_submission, sample_bundle):
        """Test bundle submission with various HTTP error status codes."""
        error_codes = [401, 403, 404, 500, 502, 503]
        
        for status_code in error_codes:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = f"Server error {status_code}"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} Error")
            mock_post.return_value = mock_response
            
            success, result = bundle_submission.submit_bundle(sample_bundle)
            
            assert success is False
            assert result["status_code"] == status_code
            assert f"Server error {status_code}" in result["response"]
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_success_different_status_codes(self, mock_post, bundle_submission, sample_bundle):
        """Test bundle submission with different successful status codes."""
        success_codes = [200, 201, 202]
        
        for status_code in success_codes:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = {"status": f"success_{status_code}"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            success, result = bundle_submission.submit_bundle(sample_bundle)
            
            assert success is True
            assert result["status"] == f"success_{status_code}"
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_json_serialization(self, mock_post, bundle_submission):
        """Test that bundle is properly JSON serialized."""
        # Complex bundle with nested structures
        complex_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "name": [{"family": "Test", "given": ["John"]}],
                        "birthDate": "1990-01-01"
                    }
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        bundle_submission.submit_bundle(complex_bundle)
        
        # Verify JSON serialization
        call_args = mock_post.call_args
        sent_data = call_args[1]['data']
        
        # Should be valid JSON string
        parsed_data = json.loads(sent_data)
        assert parsed_data == complex_bundle
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_headers_validation(self, mock_post, bundle_submission, sample_bundle):
        """Test that all required headers are included."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        bundle_submission.submit_bundle(sample_bundle)
        
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        
        # Verify all required headers
        required_headers = ['Authorization', 'Content-Type', 'Accept']
        for header in required_headers:
            assert header in headers
        
        # Verify header values
        assert headers['Authorization'].startswith('Bearer ')
        assert headers['Content-Type'] == 'application/fhir+json'
        assert headers['Accept'] == 'application/fhir+json'
        
    
    @patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post')
    def test_submit_bundle_auth_token_dynamic_retrieval(self, mock_post, bundle_submission, sample_bundle):
        """Test that auth token is retrieved dynamically for each request."""
        # Mock changing auth token
        bundle_submission.auth_client.get_token.side_effect = ["token1", "token2"]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # First submission
        bundle_submission.submit_bundle(sample_bundle)
        call1_headers = mock_post.call_args[1]['headers']
        assert call1_headers['Authorization'] == 'Bearer token1'
        
        # Second submission
        bundle_submission.submit_bundle(sample_bundle)
        call2_headers = mock_post.call_args[1]['headers']
        assert call2_headers['Authorization'] == 'Bearer token2'
        
        # Verify auth client was called twice
        assert bundle_submission.auth_client.get_token.call_count == 2


@pytest.mark.integration
class TestBundleSubmissionIntegration:
    """Integration tests for BundleSubmission."""
    
    @pytest.fixture
    def real_bundle_submission(self):
        """Create a real BundleSubmission instance for integration testing."""
        return BundleSubmission("http://integration-test:9012/fhir")
    
    def test_bundle_submission_with_real_auth(self, real_bundle_submission):
        """Test bundle submission with real auth client (mocked network)."""
        with patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "integration_success"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            sample_bundle = {"resourceType": "Bundle", "type": "transaction"}
            
            success, result = real_bundle_submission.submit_bundle(sample_bundle)
            
            assert success is True
            assert result["status"] == "integration_success"
            mock_post.assert_called_once()
    
    @pytest.mark.network
    def test_full_submission_workflow_mock_server(self, real_bundle_submission):
        """Test full submission workflow with mocked FHIR server."""
        # This would require mocking FHIR server responses
        # Skip for now unless in network testing environment
        pytest.skip("Integration test requires mocked FHIR server")
    
    def test_error_handling_integration(self, real_bundle_submission):
        """Test error handling in real scenario."""
        with patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post') as mock_post:
            # Simulate network error
            mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")
            
            sample_bundle = {"resourceType": "Bundle", "type": "transaction"}
            
            success, result = real_bundle_submission.submit_bundle(sample_bundle)
            
            assert success is False
            assert "Network unreachable" in result["error"]
    
    def test_url_handling_integration(self, real_bundle_submission):
        """Test URL handling in real scenario."""
        # Test that URL manipulation works correctly
        original_url = real_bundle_submission.esmd_fhir_server_url
        
        with patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            sample_bundle = {"resourceType": "Bundle", "type": "transaction"}
            real_bundle_submission.submit_bundle(sample_bundle)
            
            # Verify URL was properly formatted
            called_url = mock_post.call_args[0][0]
            assert called_url.endswith('/')
            assert called_url.startswith(original_url.rstrip('/'))
    
    def test_large_bundle_submission(self, real_bundle_submission):
        """Test submission of large bundles."""
        # Create a large bundle
        large_bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": []
        }
        
        # Add many entries
        for i in range(100):
            large_bundle["entry"].append({
                "fullUrl": f"Patient/patient-{i}",
                "resource": {
                    "resourceType": "Patient",
                    "id": f"patient-{i}",
                    "name": [{"family": f"Test{i}", "given": ["Patient"]}]
                },
                "request": {"method": "POST", "url": "Patient"}
            })
        
        with patch('bundlesubmissionclient.EsmdBundleSubmission.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "large_bundle_success"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            success, result = real_bundle_submission.submit_bundle(large_bundle)
            
            assert success is True
            assert result["status"] == "large_bundle_success"
            
            # Verify large bundle was properly serialized
            call_data = json.loads(mock_post.call_args[1]['data'])
            assert len(call_data["entry"]) == 100 