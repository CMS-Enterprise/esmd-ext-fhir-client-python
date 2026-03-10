"""
Unit tests for PresignedUrlGenerator in bundlesubmissionclient module.
"""

from sys import exc_info
import pytest
import os
import json
import hashlib
import base64
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from bundlesubmissionclient.PresignedUrlGenerator import PresignedUrlGenerator
from esmd_shared.config import ConfigUtility
from esmd_shared.exceptions import AuthenticationError, FileOperationError, NetworkError, PresignedUrlError, RetryExhaustedError, ValidationError


class TestPresignedUrlGenerator:
    """Test cases for PresignedUrlGenerator class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('bundlesubmissionclient.PresignedUrlGenerator.ConfigUtility') as mock_config, \
             patch('bundlesubmissionclient.PresignedUrlGenerator.EsmdAuthClient') as mock_auth:
            
            # Set up mock returns
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config_instance.get_presigned_url_base.return_value = "http://test-server:9016/fhir"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                # 'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }
    
    @pytest.fixture
    def generator(self, mock_dependencies):
        """Create PresignedUrlGenerator instance with mocked dependencies."""
        return PresignedUrlGenerator()
    
    def test_init(self, generator, mock_dependencies):
        """Test PresignedUrlGenerator initialization."""
        assert generator.base_url == "http://test-server:9012/fhir"
        assert generator.presigned_base_url == "http://test-server:9016/fhir"
        assert generator.config_util is not None
        assert generator.auth_client is not None
    
 
    
    def test_get_file_size_success(self, generator, sample_file_paths):
        """Test successful file size retrieval."""
        file_path = sample_file_paths[0]
        print(f'file_path, {file_path}')
        
        size = generator.get_file_size(file_path)
               
        assert size is not None
        assert size > 0
        assert isinstance(size, int)
    
    def test_get_file_size_file_not_found(self, generator, caplog):
        """Test file size retrieval when file doesn't exist."""
        caplog.set_level("ERROR")
        with pytest.raises(FileOperationError) as exc_info:	
            size = generator.get_file_size("nonexistent_file.xml")        
            assert size is None
        # print(f'caplog.text , {caplog.text}')
        
        # assert "File not found" in caplog.text
        assert "File not found" in str(exc_info.value)
    
    def test_generate_md5_success(self, generator, sample_file_paths):
        """Test successful MD5 hash generation."""
        file_path = sample_file_paths[0]
        
        md5_hash = generator.generate_md5(file_path)
        
        assert md5_hash is not None
        assert isinstance(md5_hash, str)
        assert len(md5_hash) > 0
        
        # Verify it's a valid base64 string
        try:
            decoded = base64.b64decode(md5_hash)
            assert len(decoded) == 16  # MD5 hash is 16 bytes
        except Exception:
            pytest.fail("MD5 hash is not valid base64")
    
    def test_generate_md5_file_not_found(self, generator, caplog):
        """Test MD5 generation when file doesn't exist."""
        with pytest.raises(FileOperationError) as exc_info:	
            md5_hash = generator.generate_md5("nonexistent_file.xml")        
            assert md5_hash is None
        assert "File not found" in str(exc_info.value)
    
    def test_generate_md5_consistency(self, generator, tmp_path):
        """Test that MD5 generation is consistent for same content."""
        # Create a test file
        test_file = tmp_path / "test_consistency.xml"
        test_content = b"Test content for MD5 consistency"
        test_file.write_bytes(test_content)
        
        # Generate MD5 multiple times
        md5_1 = generator.generate_md5(str(test_file))
        md5_2 = generator.generate_md5(str(test_file))
        
        assert md5_1 == md5_2
        
        # Verify against known MD5
        expected_md5 = base64.b64encode(hashlib.md5(test_content).digest()).decode('utf-8')
        assert md5_1 == expected_md5
    

    @patch('bundlesubmissionclient.PresignedUrlGenerator.requests.post')
    def test_generate_presigned_url_success(self, mock_post, generator, sample_file_paths):
        """Test successful presigned URL generation."""
        # Mock successful response
        generator.auth_client.get_auth_header = Mock(return_value={"Authorization": "Bearer test_access_token"})
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "fileinfo",
                    "part": [
                        {
                            "parameter": [
                                {"name": "filename", "valueString": "test_document_0.xml"},
                                {"name": "uploadUrl", "valueString": "https://s3.amazonaws.com/upload-url"}
                            ]
                        }
                    ]
                }
            ]
        }
        
        mock_response.headers = {"Authorization": "Bearer test_access_token", "Content-Type": "application/fhir+json"}
        mock_post.return_value = mock_response

        
        # Mock file operations
        with patch.object(generator, 'generate_md5', return_value='test_md5_hash'):
            result = generator.generate_presigned_url("test_id", "test_oid", sample_file_paths)
        print(f"result , {result}")
        assert result is not None
        print(f"result , {result}")
        assert result["resourceType"] == "Parameters"
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "DocumentReference/$generate-presigned-url" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer test_access_token'
        assert call_args[1]['headers']['Content-Type'] == 'application/fhir+json'        

    @patch('bundlesubmissionclient.PresignedUrlGenerator.requests.post')
    def test_generate_presigned_url_no_token(self, mock_post, generator, sample_file_paths, caplog):
        """Test presigned URL generation when no access token available."""
        generator.auth_client.get_token.return_value = None
        generator.auth_client.get_auth_header = Mock(side_effect=AuthenticationError("No access token could be retrieved"))
        
        with pytest.raises(AuthenticationError) as exc_info:
            generator.generate_presigned_url("test_id", "test_oid", sample_file_paths)
     
        mock_post.assert_not_called()

        # Check the last exception details
        assert "No access token could be retrieved" in str(exc_info.value)
    
    
    @patch('bundlesubmissionclient.PresignedUrlGenerator.requests.post')
    def test_generate_presigned_url_http_error(self, mock_post, generator, sample_file_paths, caplog):
        """Test presigned URL generation with HTTP error."""
        # Mock error response
        generator.auth_client.get_auth_header = Mock(return_value={"Authorization": "Bearer test_access_token"})
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        with patch.object(generator, 'generate_md5', return_value='test_md5_hash'):
            result = generator.generate_presigned_url("test_id", "test_oid", sample_file_paths)
        
        assert result is None
        assert "Failed to generate presigned URL" in caplog.text
        assert "Status: 400" in caplog.text
    
    @patch('bundlesubmissionclient.PresignedUrlGenerator.requests.post')
    def test_generate_presigned_url_request_exception(self, mock_post, generator, sample_file_paths, caplog):
        """Test presigned URL generation with request exception."""
        generator.auth_client.get_auth_header = Mock(return_value={"Authorization": "Bearer test_access_token"})
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
    
        with patch.object(generator, 'generate_md5', return_value='test_md5_hash'):
            with pytest.raises(NetworkError) as exc_info:
                generator.generate_presigned_url("test_id", "test_oid", sample_file_paths)
    
        assert "Network error while generating presigned URLs: Network error" in caplog.text
    
    def test_generate_presigned_url_md5_failure(self, generator, sample_file_paths, caplog):
        """Test presigned URL generation when MD5 generation fails."""
        generator.auth_client.get_auth_header = Mock(return_value={"Authorization": "Bearer test_access_token"})
        generator.timeout = 10
        with patch.object(generator, 'generate_md5', side_effect=FileOperationError("MD5 generation failed")):
            result = generator.generate_presigned_url("test_id", "test_oid", sample_file_paths)

        assert result is None
        assert "MD5 generation failed" in caplog.text
    
    def test_extract_filenames_and_tokens_success(self, generator):
        """Test successful extraction of filenames and tokens from response."""
        response_data = {
          
            "parameter": [
        {
            "name": "presignedUrls",
            "part": [
                {
                    "name": "file",
                    "part": [
                        {
                            "name": "filename",
                            "valueString": "document1.xml"
                        },
                        {
                            "name": "uploadUrl",
                            "valueUrl": "https://s3.amazonaws.com/url1"
                        }
                    ]
                },
				{
                    "name": "file",
                    "part": [
                        {
                            "name": "filename",
                            "valueString": "document2.xml"
                        },
                        {
                            "name": "uploadUrl",
                            "valueUrl": "https://s3.amazonaws.com/url2"
                        }
                    ]
                }
            ]
        },
        {
            "name": "expiresIn",
            "valueDuration": {
                "value": 900,
                "unit": "seconds",
                "system": "http://unitsofmeasure.org",
                "code": "s"
            }
        }
    ]
        }
        
        result = generator.extract_filenames_and_tokens(response_data)
        

        assert len(result) == 2
        assert result[0] == ("document1.xml", "https://s3.amazonaws.com/url1")
        assert result[1] == ("document2.xml", "https://s3.amazonaws.com/url2")
    
    def test_extract_filenames_and_tokens_incomplete_data(self, generator):
        """Test extraction with incomplete parameter data."""
        response_data = {
           "parameter": [
        {
            "name": "presignedUrls",
            "part": [
                {
                    "name": "file",
                    "part": [
                        {
                            "name": "filename",
                            "valueString": "document1.xml"
                        }
                    ]
                },
				{
                    "name": "file",
                    "part": [
                        {
                            "name": "filename",
                            "valueString": "document2.xml"
                        },
                        {
                            "name": "uploadUrl",
                            "valueUrl": "https://s3.amazonaws.com/url2"
                        }
                    ]
                }
            ]
        }
    ]
	
        }
        
        result = generator.extract_filenames_and_tokens(response_data)
        
        assert len(result) == 1  # Should skip incomplete entries
    
    def test_extract_filenames_and_tokens_empty_response(self, generator):
        """Test extraction with empty response."""
        response_data = {}
        
        with pytest.raises(ValidationError) as exc_info:
            result = generator.extract_filenames_and_tokens(response_data)
        
            assert len(result) == 0
    
    def test_extract_filenames_and_tokens_malformed_response(self, generator):
        """Test extraction with malformed response structure."""
        response_data = {
            "parameter": [
                {
                    # Missing 'part' key
                }
            ]
        }
        
        with pytest.raises(PresignedUrlError) as exc_info:
            result = generator.extract_filenames_and_tokens(response_data)
        
            assert len(result) == 0
    
    def test_generate_random_alphanumeric_default_length(self, generator):
        """Test random alphanumeric generation with default length."""
        result = generator.generate_random_alphanumeric()
        
        assert len(result) == 5
        assert result.isalnum()
        assert result.isupper()  # Should be uppercase
    
    def test_generate_random_alphanumeric_custom_length(self, generator):
        """Test random alphanumeric generation with custom length."""
        result = generator.generate_random_alphanumeric(10)
        
        assert len(result) == 10
        assert result.isalnum()
        assert result.isupper()
    
    def test_generate_random_alphanumeric_uniqueness(self, generator):
        """Test that generated strings are unique."""
        results = set()
        for _ in range(100):
            result = generator.generate_random_alphanumeric()
            results.add(result)
            print(f"result: {result}")
        
        # Should have generated mostly unique strings
        assert len(results) > 90  # Allow for some collisions
    
    # @patch('bundlesubmissionclient.PresignedUrlGenerator.PresignedUrlUploader')
    # @patch('bundlesubmissionclient.PresignedUrlGenerator.PrepareBundleSubmission')
    # @patch('bundlesubmissionclient.PresignedUrlGenerator.BundleSubmission')
    # @patch('bundlesubmissionclient.PresignedUrlGenerator.FhirResponseProcessor')
    # def test_entry_point_success(self, mock_processor, mock_bundle_sub, mock_prepare, mock_uploader, 
    #                               generator, sample_extensions_data, sample_identifiers_data, sample_file_paths):
    #     """Test successful entry point execution."""
    #     # Mock presigned URL generation
    #     with patch.object(generator, 'generate_presigned_url') as mock_gen_url, \
    #          patch.object(generator, 'extract_filenames_and_tokens') as mock_extract, \
    #          patch.object(generator, 'get_file_size', return_value=1024), \
    #          patch.object(generator, 'generate_md5', return_value='test_md5'):
            
    #         mock_gen_url.return_value = {"status": "success"}
    #         mock_extract.return_value = [("document.pdf", "https://upload-url")]
            
    #         # Mock uploader
    #         mock_uploader_instance = Mock()
    #         mock_uploader_instance.upload_file.return_value = '{"status": "SUCCESS", "filename": "document.pdf", "s3uri": "https://s3-url"}'
    #         mock_uploader.return_value = mock_uploader_instance
            
    #         # Mock bundle preparation
    #         mock_prepare_instance = Mock()
    #         mock_prepare_instance.build_bundle.return_value = {"bundle": "data"}
    #         mock_prepare.return_value = mock_prepare_instance
            
    #         # Mock bundle submission
    #         mock_bundle_sub_instance = Mock()
    #         mock_bundle_sub_instance.submit_bundle.return_value = {"response": "data"}
    #         mock_bundle_sub.return_value = mock_bundle_sub_instance
            
    #         # Mock response processor
    #         mock_processor_instance = Mock()
    #         mock_processor.return_value = mock_processor_instance
            
    #         # Execute entry point
    #         generator.entry_point("test_id", sample_extensions_data, sample_identifiers_data, sample_file_paths)
            
    #         # Verify all steps were called
    #         mock_gen_url.assert_called_once()
    #         mock_extract.assert_called_once()
    #         mock_uploader_instance.upload_file.assert_called_once()
    #         mock_prepare_instance.add_document_reference.assert_called_once()
    #         mock_prepare_instance.build_bundle.assert_called_once()
    #         mock_bundle_sub_instance.submit_bundle.assert_called_once()
    #         mock_processor_instance.process_response.assert_called_once()
    
    def test_entry_point_missing_organizationid(self, generator, sample_identifiers_data, sample_file_paths, caplog):
        """Test entry point with missing OrganizationIdValue."""
        caplog.set_level("ERROR")
        extensions_data = {"other_key": "other_value"}  # Missing OrganizationIdValue
        
        generator.entry_point("test_id", extensions_data, sample_identifiers_data, sample_file_paths)

        assert "OrganizationIdValue is missing from extensions_data" in caplog.text

    def test_entry_point_presigned_url_failure(self, generator, sample_extensions_data,
                                               sample_identifiers_data, sample_file_paths, caplog):
        """Test entry point when presigned URL generation fails."""
        with patch.object(generator, 'generate_presigned_url', return_value=None):
             generator.entry_point("test_id", sample_extensions_data, sample_identifiers_data, sample_file_paths)
             
            # Should return early when presigned URL generation fails
             assert "Failed to generate presigned URL" in caplog.text

    def test_entry_point_extraction_failure(self, generator, sample_extensions_data,
                                            sample_identifiers_data, sample_file_paths, caplog):
        """Test entry point when filename/token extraction fails."""
        with patch.object(generator, 'generate_presigned_url', return_value={"status": "success"}), \
             patch.object(generator, 'extract_filenames_and_tokens', return_value=[]):
            
            generator.entry_point("test_id", sample_extensions_data, sample_identifiers_data, sample_file_paths)

            assert "Failed to extract filenames and upload URLs" in caplog.text

    def test_entry_point_exception_handling(self, generator, sample_extensions_data,
                                            sample_identifiers_data, sample_file_paths, caplog):
        """Test entry point exception handling."""
        with patch.object(generator, 'generate_presigned_url', side_effect=Exception("Test exception")):
            generator.entry_point("test_id", sample_extensions_data, sample_identifiers_data, sample_file_paths)

            assert "An unexpected error occurred during processing" in caplog.text
            assert "Test exception" in caplog.text


@pytest.mark.integration

class TestPresignedUrlGeneratorIntegration:
    """Integration tests for PresignedUrlGenerator."""
    
    @pytest.fixture
    def real_generator(self):
        """Create a real PresignedUrlGenerator instance for integration testing."""
        return PresignedUrlGenerator()
    
    def test_md5_generation_with_real_files(self, real_generator, sample_file_paths):
        """Test MD5 generation with real files."""
        md5_hash = real_generator.generate_md5(sample_file_paths[0])
        
        assert md5_hash is not None
        assert isinstance(md5_hash, str)
        
        # Verify it's valid base64
        decoded = base64.b64decode(md5_hash)
        assert len(decoded) == 16
    
    def test_file_size_with_real_files(self, real_generator, sample_file_paths):
        """Test file size calculation with real files."""
        size = real_generator.get_file_size(sample_file_paths[0])
        
        assert size is not None
        assert size > 0
        assert isinstance(size, int)
    
    # @pytest.mark.network
    # def test_full_workflow_mock_external_services(self, real_generator, sample_extensions_data, 
    #                                               sample_identifiers_data, sample_file_paths):
    #     """Test full workflow with mocked external services."""
    #     # This would require mocking the FHIR server and S3 responses
    #     # Skip for now unless in network testing environment
    #     pytest.skip("Integration test requires mocked external services")
    
    def test_random_id_generation_uniqueness(self, real_generator):
        """Test uniqueness of random ID generation in real scenario."""
        ids = set()
        for _ in range(1000):
            bundle_id = "bundle-" + real_generator.generate_random_alphanumeric(5)
            list_id = "list-" + real_generator.generate_random_alphanumeric(5)
            ids.add((bundle_id, list_id))
        
        # Should have generated all unique pairs
        assert len(ids) == 1000 

    def test_generate_presigned_urls_structured_realtime(self, real_generator, sample_file_paths):
        # Create a temporary file to upload
        file_paths = sample_file_paths

        # Prepare the structured request
        from esmd_shared.models import PresignedUrlRequest
        from bundlesubmissionclient.PresignedUrlUploader import PresignedUrlUploader

        request = PresignedUrlRequest(
            file_paths=file_paths,
            metadata={"organizationid": "urn:oid:123.456.657.126"}
        )

        # Call the method
        response = real_generator.generate_presigned_urls_structured(request)

        print(f"Response: {response}")
        # Basic assertions
        assert response.transaction_id.startswith("presigned-")
        assert len(response.urls) == len(file_paths)
        for url_info in response.urls:
            assert url_info.file_path in file_paths
            assert url_info.presigned_url.startswith("https://")
            assert url_info.md5_hash is not None
            assert url_info.file_size is not None
            assert url_info.content_type is not None

        # Upload files using the presigned URLs
        uploader = PresignedUrlUploader()
        for info in response.urls:
            response = uploader.upload_file(info.presigned_url , info.file_path, info.md5_hash, info.file_size, info.content_type)
            print(f"Upload response: {response}")
            resp_json = json.loads(response)
            assert resp_json["status"] == "SUCCESS"
            assert resp_json["message"] == "FILE UPLOADED SUCCESSFULLY"
            assert resp_json["filename"] is not None
            assert resp_json["s3uri"].startswith("s3://")

    def test_bundle_submission_with_real_time_data(self, real_generator, sample_extensions_data, sample_identifiers_data, sample_file_paths,caplog):
        """Test bundle submission with real-time data."""
        config = ConfigUtility()
        #real_generator = PresignedUrlGenerator()
        unique_id = f"presigned-{real_generator.generate_random_alphanumeric(8)}"
        response = real_generator.entry_point(unique_id, sample_extensions_data, sample_identifiers_data, sample_file_paths)
        print("Integration test completed. See logs for details. {response}")

        assert response.get("valid")
        assert "Transaction ID extracted:" in caplog.text
        assert "Process completed successfully." in caplog.text
