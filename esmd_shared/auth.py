"""
Enhanced EsmdAuthClient for OAuth2 authentication with esMD services.

This module provides a robust authentication client with improved error handling,
type hints, validation, retry logic, and circuit breaker patterns.
"""

import time
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import requests

from .config import ConfigUtility
from .models import (
    AuthConfig, TokenInfo, HTTPRequest, HTTPResponse, 
    RetryConfig, CircuitBreakerConfig, ValidationResult, HTTPMethod
)
from .exceptions import (
    AuthenticationError, RetryExhaustedError, TokenExpiredError, ValidationError,
    NetworkError, ConfigurationError
)
from .utils import (
    retry_with_backoff, CircuitBreaker, validate_required_fields,
    validate_url, is_expired, PerformanceMonitor
)


class EsmdAuthClient:
    """OAuth2 authentication client for esMD services with advanced features."""
    
    def __init__(
        self, 
        config_util: Optional[ConfigUtility] = None,
        retry_config: Optional[RetryConfig] = None,
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize the EsmdAuthClient.
        
        Args:
            config_util: Optional ConfigUtility instance. If None, creates a new one.
            retry_config: Optional retry configuration for failed requests.
            enable_circuit_breaker: Whether to enable circuit breaker pattern.
            
        Raises:
            ConfigurationError: If required configuration is missing.
            ValidationError: If configuration values are invalid.
        """
        self.config_util = config_util or ConfigUtility()
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = PerformanceMonitor()
        
        # Retry configuration
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            backoff_factor=1.0,
            retry_statuses=[500, 502, 503, 504, 429],
            timeout=30
        )
        
        # Circuit breaker configuration
        if enable_circuit_breaker:
            circuit_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=NetworkError
            )
            self.circuit_breaker = CircuitBreaker(circuit_config)
        else:
            self.circuit_breaker = None
        
        # Load and validate configurations
        self._load_configuration()
        
        # Token storage
        self._token_info: Optional[TokenInfo] = None
        
    def _load_configuration(self) -> None:
        """Load and validate authentication configuration."""
        try:
            # Get configuration values
            auth_url = self.config_util.get_token_endpoint()
            client_id = self.config_util.get_client_id()
            client_secret = self.config_util.get_client_secret()
            scope = self.config_util.get_scope()
            
            # Validate required fields
            config_dict = {
                'token_endpoint': auth_url,
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            validation = validate_required_fields(
                config_dict, 
                ['token_endpoint', 'client_id', 'client_secret']
            )
            
            if not validation.is_valid:
                raise ConfigurationError(
                    f"Missing required configuration: {', '.join(validation.errors)}",
                    missing_keys=list(validation.field_errors.keys())
                )
            
            # Validate URL format
            url_validation = validate_url(auth_url)
            if not url_validation.is_valid:
                raise ValidationError(
                    f"Invalid token endpoint URL: {auth_url}",
                    field="token_endpoint",
                    value=auth_url
                )
            
            # Store validated configuration
            self.auth_config = AuthConfig(
                client_id=client_id,
                client_secret=client_secret,
                token_endpoint=auth_url,
                scope=scope,
                timeout=self.retry_config.timeout
            )
            
            self.logger.info(f"Authentication configuration loaded for endpoint: {auth_url}")
            
        except Exception as e:
            if isinstance(e, (ConfigurationError, ValidationError)):
                raise e
            raise ConfigurationError(f"Failed to load authentication configuration: {e}")
    
    def _is_token_valid(self) -> bool:
        """
        Check if the current token is still valid.
        
        Returns:
            bool: True if token is valid and not expired, False otherwise.
        """
        if not self._token_info:
            return False
        
        return not is_expired(self._token_info.expires_at)
    
    def _create_token_request(self) -> HTTPRequest:
        """Create HTTP request for token acquisition."""
        headers = {
            'clientid': self.auth_config.client_id,
            'clientsecret': self.auth_config.client_secret,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Refyne-FHIR-Client/1.0'
        }
        
        if self.auth_config.scope:
            headers['scope'] = self.auth_config.scope
        
        return HTTPRequest(
            method=HTTPMethod.POST,
            url=self.auth_config.token_endpoint,
            headers=headers,
            data={},
            timeout=self.auth_config.timeout,
            verify_ssl=True
        )
    
    def _request_token(self) -> TokenInfo:
        """
        Request a new token from the authentication server.
        
        Returns:
            TokenInfo: Token information including expiration.
            
        Raises:
            AuthenticationError: If authentication fails.
            NetworkError: If network request fails.
        """
        request = self._create_token_request()
        
        # Enhanced audit logging
        self.logger.info(f"[AUDIT] Initiating token request to {self.auth_config.token_endpoint}")
        self.logger.info(f"[AUDIT] Client ID: {self.auth_config.client_id[:8]}... (truncated)")
        self.logger.info(f"[AUDIT] Scope: {self.auth_config.scope}")
        self.logger.info("Requesting new token from esMD Auth API...")
        
        try:
            response = requests.request(
                method=request.method.value,
                url=request.url,
                headers=request.headers,
                data=request.data,
                params=request.params,
                timeout=request.timeout,
                verify=request.verify_ssl
            )
            
            # Create response object
            http_response = HTTPResponse(
                status_code=response.status_code,
                text=response.text,
                headers=dict(response.headers),
                url=response.url,
                elapsed_seconds=response.elapsed.total_seconds()
            )
            
            # Check for HTTP errors
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed: Invalid client credentials",
                    token_endpoint=self.auth_config.token_endpoint
                )
            elif response.status_code >= 400:
                raise AuthenticationError(
                    f"Authentication failed with status {response.status_code}: {response.text}",
                    token_endpoint=self.auth_config.token_endpoint
                )
            
            # Parse response
            try:
                token_data = response.json()
            except ValueError as e:
                raise AuthenticationError(f"Invalid JSON response from auth server: {e}")
            
            # Validate token response
            if 'access_token' not in token_data:
                raise AuthenticationError("No access token in response")
            
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 1800)  # Default to 30 mins
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            token_info = TokenInfo(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_at=expires_at,
                scope=token_data.get('scope'),
                refresh_token=token_data.get('refresh_token')
            )
            
            # Enhanced audit logging for successful token retrieval
            self.logger.info(f"[AUDIT] Token retrieved successfully. Expires at {expires_at}")
            self.logger.info(f"[AUDIT] Token type: {token_info.token_type}")
            self.logger.info(f"[AUDIT] Token scope: {token_info.scope}")
            self.logger.info(f"Token retrieved successfully. Expires at {expires_at}")
            return token_info
            
        except requests.exceptions.Timeout:
            raise NetworkError(
                "Request timed out while getting token",
                url=self.auth_config.token_endpoint,
                method="POST"
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Connection error while getting token: {e}",
                url=self.auth_config.token_endpoint,
                method="POST"
            )
        except requests.exceptions.RequestException as e:
            raise NetworkError(
                f"Network error while getting token: {e}",
                url=self.auth_config.token_endpoint,
                method="POST"
            )
    
    def _get_token_with_retry(self) -> TokenInfo:
        """Get token with retry logic and circuit breaker."""
        @retry_with_backoff(self.retry_config)
        def _get_token():
            if self.circuit_breaker:
                return self.circuit_breaker(self._request_token)()
            else:
                return self._request_token()
        
        return _get_token()
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        Retrieve a valid OAuth2 token using client credentials flow.
        
        Args:
            force_refresh: If True, forces token refresh even if current token is valid.
            
        Returns:
            str: Access token.
            
        Raises:
            AuthenticationError: If authentication fails.
            TokenExpiredError: If token is expired and refresh fails.
            NetworkError: If network requests fail.
        """
        # Return cached token if still valid and not forcing refresh
        if not force_refresh and self._is_token_valid() and self._token_info:
            self.logger.debug("Using cached access token")
            return self._token_info.access_token
        
        # Check if we have an expired token
        if self._token_info and is_expired(self._token_info.expires_at) and not force_refresh:
            raise TokenExpiredError("Access token has expired")
        
        try:
            # Get new token
            self._token_info = self._get_token_with_retry()
            return self._token_info.access_token
        
        except RetryExhaustedError as e:
            self._token_info = None
            last_exc_msg = ""
            if hasattr(e, "last_exception") and e.last_exception:
                last_exc_msg = f" | Last error: {e.last_exception}"
            if isinstance(getattr(e, "last_exception", None), AuthenticationError):
                raise AuthenticationError(
            f"Authentication failed after retries: {e.last_exception}"
        ) from e
            elif isinstance(getattr(e, "last_exception", None), NetworkError):
                raise NetworkError(
            f"Network error after retries: {e.last_exception}"
        ) from e
            else:
                raise AuthenticationError(
            f"All retry attempts failed during token acquisition: {e}{last_exc_msg}"
        ) from e

        except (AuthenticationError, NetworkError) as e:
            self._token_info = None
            raise e

        except Exception as e:
            self._token_info = None
            raise AuthenticationError(
                f"Unexpected error during token acquisition: {e}"
            ) from e
    
    def get_auth_header(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get authorization header for API requests.
        
        Args:
            force_refresh: If True, forces token refresh even if current token is valid.
        
        Returns:
            Dict[str, str]: Authorization header dictionary.
            
        Raises:
            AuthenticationError: If authentication fails.
            TokenExpiredError: If token is expired and refresh fails.
        """
        token = self.get_token(force_refresh=force_refresh)
        token_type = self._token_info.token_type if self._token_info else "Bearer"
        return {'Authorization': f'{token_type} {token}'}
    
    def revoke_token(self) -> bool:
        """
        Revoke the current token and clear cached credentials.
        
        Returns:
            bool: True if successful.
        """
        if self._token_info:
            self.logger.info("Revoking cached token")
        
        self._token_info = None
        self.logger.info("Token cache cleared")
        return True
    
    def get_token_info(self) -> Optional[TokenInfo]:
        """
        Get current token information.
        
        Returns:
            Optional[TokenInfo]: Current token info or None if no token.
        """
        return self._token_info
    
    def is_authenticated(self) -> bool:
        """
        Check if client is currently authenticated with a valid token.
        
        Returns:
            bool: True if authenticated with valid token, False otherwise.
        """
        return self._is_token_valid()
    
    def get_performance_metrics(self):
        """Get performance metrics for authentication operations."""
        return self.performance_monitor.get_metrics()
    
    def validate_configuration(self) -> ValidationResult:
        """
        Validate the current authentication configuration.
        
        Returns:
            ValidationResult: Validation result with any errors or warnings.
        """
        result = ValidationResult(is_valid=True)
        
        # Check if configuration is loaded
        if not hasattr(self, 'auth_config'):
            result.errors.append("Authentication configuration not loaded")
            result.is_valid = False
            return result
        
        # Validate URL
        url_validation = validate_url(self.auth_config.token_endpoint)
        if not url_validation.is_valid:
            result.errors.extend(url_validation.errors)
            result.field_errors.update(url_validation.field_errors)
        
        # Check timeout values
        if self.auth_config.timeout <= 0:
            result.warnings.append("Timeout value is very low, may cause request failures")
        
        result.is_valid = len(result.errors) == 0
        return result 