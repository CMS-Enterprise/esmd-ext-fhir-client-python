"""
Unit tests for PresignedUrlUploader in bundlesubmissionclient module.
"""

import pytest
import os
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from bundlesubmissionclient.PresignedUrlUploader import PresignedUrlUploader


class TestPresignedUrlUploader:
    """Test cases for PresignedUrlUploader class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('bundlesubmissionclient.PresignedUrlUploader.setup_logger') as mock_logger, \
             patch('bundlesubmissionclient.PresignedUrlUploader.ConfigUtility') as mock_config, \
             patch('bundlesubmissionclient.PresignedUrlUploader.EsmdAuthClient') as mock_auth:
            
            # Set up mock returns
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }
    
    @pytest.fixture
    def uploader(self, mock_dependencies):
        """Create PresignedUrlUploader instance with mocked dependencies."""
        return PresignedUrlUploader()
    
    def test_init(self, uploader, mock_dependencies):
        """Test PresignedUrlUploader initialization."""
        assert uploader.base_url == "http://test-server:9012/fhir"
        assert uploader.config_util is not None
        assert uploader.auth_client is not None
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test file content")
    def test_upload_file_success(self, mock_file_open, mock_exists, mock_post, uploader):
        """Test successful file upload."""
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "SUCCESS", "message": "File uploaded successfully"}'
        mock_post.return_value = mock_response
        
        # Test parameters
        presigned_url = "https://s3.amazonaws.com/test-bucket/upload"
        file_path = "/path/to/test_file.pdf"
        md5_hash = "test_md5_hash"
        content_length = 1024
        content_type = "application/pdf"
        
        # Execute upload
        result = uploader.upload_file(presigned_url, file_path, md5_hash, content_length, content_type)
        
        # Verify result
        assert result == '{"status": "SUCCESS", "message": "File uploaded successfully"}'
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == presigned_url
        
        # Verify headers
        headers = call_args[1]['headers']
        assert headers['Content-Type'] == 'application/pdf'
        assert headers['Authorization'] == 'Bearer test_access_token'
        assert headers['content-md5'] == 'test_md5_hash'
        assert headers['content-length'] == '1024'
        
        # Verify file was opened for reading
        mock_file_open.assert_called_once_with(file_path, 'rb')
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    def test_upload_file_not_found(self, mock_exists, uploader, capsys):
        """Test file upload when file doesn't exist."""
        mock_exists.return_value = False
        
        result = uploader.upload_file(
            "https://test-url", 
            "/nonexistent/file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        captured = capsys.readouterr()
        assert "File not found" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_no_token(self, mock_file_open, mock_exists, mock_post, uploader, caplog):
        """Test file upload when no access token available."""
        caplog.set_level("ERROR")
        mock_exists.return_value = True
        uploader.auth_client.get_token.return_value = None
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        #assert "No access token could be retrieved, aborting request." in caplog.text
        mock_post.assert_not_called()
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_http_error(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with HTTP error response."""
        mock_exists.return_value = True
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result == "Bad Request"
        captured = capsys.readouterr()
        assert "Failed to upload file. Status code: 400" in captured.out
        assert "Bad Request" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_server_error(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with server error response."""
        mock_exists.return_value = True
        
        # Mock server error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result == "Internal Server Error"
        captured = capsys.readouterr()
        assert "Failed to upload file. Status code: 500" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_request_exception(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with request exception."""
        mock_exists.return_value = True
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        captured = capsys.readouterr()
        assert "Error during the upload request: Network error" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_timeout(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with timeout exception."""
        mock_exists.return_value = True
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        captured = capsys.readouterr()
        assert "Error during the upload request: Request timed out" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_connection_error(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with connection error."""
        mock_exists.return_value = True
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        captured = capsys.readouterr()
        assert "Error during the upload request: Connection failed" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_default_content_type(self, mock_file_open, mock_exists, mock_post, uploader):
        """Test file upload with default content type."""
        mock_exists.return_value = True
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.bin", 
            "hash", 
            1024
            # No content_type parameter - should use default
        )
        
        assert result == "Success"
        
        # Verify default content type was used
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        assert headers['Content-Type'] == 'application/octet-stream'
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_custom_content_type(self, mock_file_open, mock_exists, mock_post, uploader):
        """Test file upload with custom content type."""
        mock_exists.return_value = True
        
        mock_response = Mock()
        mock_response.status_code = 201  # Different success code
        mock_response.text = "Created"
        mock_post.return_value = mock_response
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.jpg", 
            "hash", 
            2048,
            content_type='image/jpeg'
        )
        
        assert result == "Created"
        
        # Verify custom content type was used
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        assert headers['Content-Type'] == 'image/jpeg'
        assert headers['content-length'] == '2048'
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_upload_file_io_error(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with file I/O error."""
        mock_exists.return_value = True
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/protected_file.pdf", 
            "hash", 
            1024
        )
        
        assert result is None
        captured = capsys.readouterr()
        assert "Permission denied" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    def test_upload_file_file_not_found_exception(self, mock_exists, mock_post, uploader, capsys):
        """Test file upload with FileNotFoundError during open."""
        mock_exists.return_value = True  # exists() returns True but open fails
        
        with patch('builtins.open', side_effect=FileNotFoundError("File disappeared")):
            result = uploader.upload_file(
                "https://test-url", 
                "/path/to/file.pdf", 
                "hash", 
                1024
            )
        
        assert result is None
        captured = capsys.readouterr()
        assert "Error: File disappeared" in captured.out
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"large file content")
    def test_upload_file_large_content_length(self, mock_file_open, mock_exists, mock_post, uploader):
        """Test file upload with large content length."""
        mock_exists.return_value = True
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        large_size = 1024 * 1024 * 100  # 100MB
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/large_file.zip", 
            "hash", 
            large_size,
            content_type='application/zip'
        )
        
        assert result == "Success"
        
        # Verify large content length was set correctly
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        assert headers['content-length'] == str(large_size)
    
    @patch('bundlesubmissionclient.PresignedUrlUploader.requests.post')
    @patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test content")
    def test_upload_file_edge_case_status_codes(self, mock_file_open, mock_exists, mock_post, uploader, capsys):
        """Test file upload with edge case status codes."""
        mock_exists.return_value = True
        
        # Test status code 299 (still success)
        mock_response = Mock()
        mock_response.status_code = 299
        mock_response.text = "Success at boundary"
        mock_post.return_value = mock_response
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result == "Success at boundary"
        captured = capsys.readouterr()
        assert "successfully uploaded" in captured.out
        
        # Test status code 300 (not success)
        mock_response.status_code = 300
        mock_response.text = "Redirection"
        
        result = uploader.upload_file(
            "https://test-url", 
            "/path/to/file.pdf", 
            "hash", 
            1024
        )
        
        assert result == "Redirection"
        captured = capsys.readouterr()
        assert "Failed to upload file. Status code: 300" in captured.out


@pytest.mark.integration
class TestPresignedUrlUploaderIntegration:
    """Integration tests for PresignedUrlUploader."""
    
    @pytest.fixture
    def real_uploader(self):
        """Create a real PresignedUrlUploader instance for integration testing."""
        return PresignedUrlUploader()
    
    def test_upload_with_real_file(self, real_uploader, sample_file_paths):
        """Test upload functionality with real files (mocked network)."""
        with patch('bundlesubmissionclient.PresignedUrlUploader.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "Success"
            mock_post.return_value = mock_response
            
            result = real_uploader.upload_file(
                "https://mock-s3-url", 
                sample_file_paths[0], 
                "test_hash", 
                os.path.getsize(sample_file_paths[0]),
                content_type='application/pdf'
            )
            
            assert result == "Success"
            mock_post.assert_called_once()
    
    @pytest.mark.network
    def test_full_upload_workflow_mock_s3(self, real_uploader, sample_file_paths):
        """Test full upload workflow with mocked S3 service."""
        # This would require mocking S3 service
        # Skip for now unless in network testing environment
        pytest.skip("Integration test requires mocked S3 service")
    
    def test_auth_token_integration(self, real_uploader):
        """Test that auth token is properly retrieved and used."""
        with patch('bundlesubmissionclient.PresignedUrlUploader.requests.post') as mock_post, \
             patch('bundlesubmissionclient.PresignedUrlUploader.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=b"test")):
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "Success"
            mock_post.return_value = mock_response
            
            with patch.object(real_uploader.auth_client, 'get_token', return_value="integration_test_token"):
                result = real_uploader.upload_file(
                    "https://test-url",
                    "/test/file.pdf",
                "hash", 
                1024
            )
            
            # Verify token was used
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer integration_test_token' 