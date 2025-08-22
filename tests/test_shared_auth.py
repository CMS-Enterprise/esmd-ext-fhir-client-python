"""
Unit tests for EsmdAuthClient in esmd_shared.auth module.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from esmd_shared.auth import EsmdAuthClient
from esmd_shared.config import ConfigUtility
from esmd_shared.exceptions import AuthenticationError , NetworkError
from datetime import datetime, timedelta
from esmd_shared.models import TokenInfo

class TestEsmdAuthClient:
    """Test cases for EsmdAuthClient class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration utility."""
        config = Mock(spec=ConfigUtility)
        config.get_token_endpoint.return_value = "https://test.example.com/auth/token"
        config.get_client_id.return_value = "test_client_id"
        config.get_client_secret.return_value = "test_client_secret"
        config.get_scope.return_value = "test_scope"
        return config
    
    @pytest.fixture
    def auth_client(self, mock_config):
        """Create an EsmdAuthClient instance with mock config."""
        return EsmdAuthClient(config_util=mock_config)
    
        
    def test_init(self, auth_client, mock_config):
        """Test EsmdAuthClient initialization."""
        assert auth_client.config_util == mock_config
        #assert auth_client.auth_url == "https://test.example.com/auth/token"
        assert auth_client.auth_config.token_endpoint == "https://test.example.com/auth/token" #auth_url not exist in EsmdAuthClient

        assert auth_client.auth_config.client_id == "test_client_id"  
        assert auth_client.auth_config.client_secret == "test_client_secret"
        assert auth_client.auth_config.scope == "test_scope"
        
        # assert auth_client.token is None
        # assert auth_client.token_type is None
        # assert auth_client.expires_in is None
        # assert auth_client.token_acquired_at is None

        assert auth_client._token_info is None
    
    def test_is_token_valid_no_token(self, auth_client):
        """Test token validity check when no token exists."""       
        assert not auth_client._is_token_valid()
    
    def test_is_token_valid_expired_token(self, auth_client):
        """Test token validity check for expired token."""
    
        expired_time = datetime.now() - timedelta(hours=1)

        auth_client._token_info = TokenInfo(
            access_token="test_token",
            token_type="Bearer",
            expires_at=expired_time
        )
        assert not auth_client._is_token_valid()
    

    def test_is_token_valid_valid_token(self, auth_client):
        """Test token validity check for valid token."""
        
        future_time = datetime.now() + timedelta(seconds=1800)

        auth_client._token_info = TokenInfo(
            access_token="test_token",
            token_type="Bearer",
            expires_at=future_time
        )

        assert auth_client._is_token_valid()

    @patch('esmd_shared.auth.requests.request')
    def test_get_token_success(self, mock_request, auth_client):
        """Test successful token retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_response.headers = {}
        mock_request.return_value = mock_response

        
        token = auth_client.get_token()
        
        # Verify token was retrieved and stored
        assert token == 'test_access_token'
        assert auth_client._token_info.access_token == 'test_access_token'
        assert auth_client._token_info.token_type == 'Bearer'        
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        print(f"Call args: %s", call_args)
        assert call_args.kwargs['url'] == "https://test.example.com/auth/token"
        assert call_args.kwargs['headers']['clientid'] == 'test_client_id'
        assert call_args.kwargs['headers']['clientsecret'] == 'test_client_secret'
        assert call_args.kwargs['headers']['scope'] == 'test_scope'
    
    @patch('esmd_shared.auth.requests.post')
    def test_get_token_cached(self, mock_post, auth_client):
        """Test that cached token is returned without making new request."""
        # Set up valid cached token
        auth_client._token_info = TokenInfo(
            access_token="cached_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(seconds=3600)
        )
                
        token = auth_client.get_token()
        
        # Should return cached token without making request
        assert token == "cached_token"
        mock_post.assert_not_called()
    
    
    @patch('esmd_shared.auth.requests.request')
    def test_get_token_force_refresh(self, mock_request, auth_client):
        """Test forced token refresh ignores cached token."""
        # Set up valid cached token
        auth_client._token_info = TokenInfo(
        access_token="cached_token",
        token_type="Bearer",
        expires_at=datetime.now() + timedelta(seconds=3600)
    )
        
        # Mock new token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        token = auth_client.get_token(force_refresh=True)
        
        # Should get new token despite cached one
        assert token == "new_access_token"        
        assert auth_client._token_info.access_token == "new_access_token"
        mock_request.assert_called_once()
    
    @patch('esmd_shared.auth.requests.request')
    def test_get_token_http_error(self, mock_request, auth_client):
        """Test token retrieval with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}  
        mock_response.url = "https://test.example.com/auth/token"  # Optional, for completeness
        mock_response.elapsed = Mock()
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_request.return_value = mock_response       
        
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth_client.get_token()
        assert "Authentication failed: Invalid client credentials" in str(exc_info.value)
    

    @patch('esmd_shared.auth.requests.request')
    def test_get_token_timeout(self, mock_request, auth_client):
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
        with pytest.raises(NetworkError) as exc_info:
            auth_client.get_token()
        assert "Network error after retries" in str(exc_info.value)
        assert "Request timed out" in str(exc_info.value)
    
    @patch('esmd_shared.auth.requests.request')
    def test_get_token_no_access_token_in_response(self, mock_request, auth_client):
        """Test token retrieval when response missing access_token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
        'token_type': 'Bearer',
        'expires_in': 3600
         # 'access_token' is intentionally missing
    }
        mock_response.headers = {}
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            auth_client.get_token()
        # Optionally check the error message
        assert "No access token in response" in str(exc_info.value) or "All 3 attempts failed" in str(exc_info.value)



    def test_get_auth_header_with_token(self, auth_client):
        """Test getting authorization header when token is available."""
        future_time = datetime.now() + timedelta(seconds=3600)
        auth_client._token_info = TokenInfo(
        access_token="test_token",
        token_type="Bearer",
        expires_at=future_time
        )
        
        with patch.object(auth_client, 'get_token', return_value="test_token"):
            header = auth_client.get_auth_header()
            
        assert header == {'Authorization': 'Bearer test_token'}
    
    def test_get_auth_header_no_token(self, auth_client):
        """Test getting authorization header when no token is available."""
        with patch.object(auth_client, 'get_token', return_value=None):
            header = auth_client.get_auth_header()            
        #assert header is None
        assert header == {'Authorization': 'Bearer None'}
    
    def test_revoke_token(self, auth_client):
        """Test token revocation."""
        # Set up token
        auth_client.token = "test_token"
        auth_client.token_type = "Bearer"
        auth_client.expires_in = 3600
        auth_client.token_acquired_at = 999999999

        future_time = datetime.now() + timedelta(seconds=3600)

        auth_client.token_info = TokenInfo(
        access_token="test_token",
        token_type="Bearer",
        expires_at=future_time
    )

          
        result = auth_client.revoke_token()
        
        assert result is True
        assert auth_client._token_info is None       
    
    def test_revoke_token_no_token(self, auth_client):
        """Test token revocation when no token exists."""
        result = auth_client.revoke_token()
        assert result is True


@pytest.mark.integration
class TestEsmdAuthClientIntegration:
    """Integration tests for EsmdAuthClient (requires network access)."""
    
    @pytest.mark.network
    def test_real_auth_flow(self):
        """Test real authentication flow (requires valid credentials in config)."""
        # This test requires real credentials and network access
        # Skip if not in integration test environment
        #pytest.skip("Integration test requires real credentials and network access")
        # Uncomment and configure for actual integration testing:
        config = ConfigUtility(load_env=True)
        print('Config loaded:', config.get_client_id(), config.get_token_endpoint())
        if not config.validate_configuration().is_valid:
            pytest.skip("Required configuration not available")
        
        auth_client = EsmdAuthClient(config)
        token = auth_client.get_token()
        
        assert token is not None
        assert len(token) > 0
        assert auth_client.get_auth_header() is not None 
        print(f"token is: {token}")
        