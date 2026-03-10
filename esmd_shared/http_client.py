"""
Enhanced HTTP Client for EsmdFHIRClient.

This module provides a robust HTTP client with retry logic, circuit breaker patterns,
performance monitoring, and comprehensive error handling.
"""

import time
import logging
from typing import Optional, Dict, Any, Union, Callable
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    HTTPRequest, HTTPResponse, RetryConfig, CircuitBreakerConfig,
    PerformanceMetrics, FHIRServerConfig
)
from .exceptions import (
    NetworkError, AuthenticationError, FHIRServerError,
    RetryExhaustedError, CircuitBreakerOpenError
)
from .utils import CircuitBreaker, PerformanceMonitor


class EnhancedHTTPClient:
    """
    Enhanced HTTP client with comprehensive features.
    
    Features:
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Performance monitoring
    - Request/response logging
    - Connection pooling
    - Timeout handling
    - Custom error handling
    """
    
    def __init__(
        self,
        server_config: Optional[FHIRServerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        enable_circuit_breaker: bool = True,
        enable_performance_monitoring: bool = True
    ):
        """
        Initialize the enhanced HTTP client.
        
        Args:
            server_config: Server configuration
            retry_config: Retry configuration
            enable_circuit_breaker: Whether to enable circuit breaker
            enable_performance_monitoring: Whether to enable performance monitoring
        """
        self.logger = logging.getLogger(__name__)
        self.server_config = server_config or FHIRServerConfig(base_url="http://localhost")
        self.retry_config = retry_config or RetryConfig()
        
        # Setup session with connection pooling and retries
        self.session = self._create_session()
        
        # Circuit breaker
        if enable_circuit_breaker:
            circuit_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=NetworkError
            )
            self.circuit_breaker = CircuitBreaker(circuit_config)
        else:
            self.circuit_breaker = None
        
        # Performance monitoring
        if enable_performance_monitoring:
            self.performance_monitor = PerformanceMonitor()
        else:
            self.performance_monitor = None
        
        self.request_count = 0
        self.error_count = 0
        
    def _create_session(self) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_config.max_attempts,
            backoff_factor=self.retry_config.backoff_factor,
            status_forcelist=self.retry_config.retry_statuses,
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Create adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        # Mount adapter for HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(self.server_config.headers)
        
        return session
    
    def _log_request(self, request: HTTPRequest) -> None:
        """Log HTTP request details."""
        self.logger.debug(
            f"HTTP Request: {request.method.value} {request.url} "
            f"(timeout={request.timeout}s)"
        )
        
        # Log headers (excluding sensitive data)
        safe_headers = {k: v for k, v in request.headers.items() 
                       if k.lower() not in ['authorization', 'x-api-key']}
        if safe_headers:
            self.logger.debug(f"Request headers: {safe_headers}")
    
    def _log_response(self, response: HTTPResponse, duration_ms: float) -> None:
        """Log HTTP response details."""
        self.logger.debug(
            f"HTTP Response: {response.status_code} "
            f"({duration_ms:.2f}ms, {len(response.text)} bytes)"
        )
        
        if response.status_code >= 400:
            self.logger.warning(f"HTTP Error Response: {response.text[:500]}")
    
    def _create_http_response(
        self, 
        response: requests.Response, 
        start_time: datetime
    ) -> HTTPResponse:
        """Create HTTPResponse object from requests.Response."""
        end_time = datetime.now()
        elapsed_seconds = (end_time - start_time).total_seconds()
        
        return HTTPResponse(
            status_code=response.status_code,
            text=response.text,
            headers=dict(response.headers),
            url=str(response.url),
            elapsed_seconds=elapsed_seconds
        )
    
    def _handle_response_error(self, response: HTTPResponse, request: HTTPRequest) -> None:
        """Handle HTTP response errors."""
        if response.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {response.text}",
                token_endpoint=request.url
            )
        elif response.status_code == 403:
            raise AuthenticationError(
                f"Access forbidden: {response.text}",
                token_endpoint=request.url
            )
        elif response.status_code >= 500:
            raise FHIRServerError(
                f"Server error: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
                url=request.url
            )
        elif response.status_code >= 400:
            raise FHIRServerError(
                f"Client error: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
                url=request.url
            )
    
    def _make_request_impl(self, request: HTTPRequest) -> HTTPResponse:
        """Make the actual HTTP request."""
        start_time = datetime.now()
        
        try:
            self._log_request(request)
            
            # Make request
            response = self.session.request(
                method=request.method.value,
                url=request.url,
                headers=request.headers,
                params=request.params,
                data=request.data,
                timeout=request.timeout,
                verify=request.verify_ssl
            )
            
            # Create response object
            http_response = self._create_http_response(response, start_time)
            
            # Log response
            duration_ms = (http_response.elapsed_seconds or 0) * 1000
            self._log_response(http_response, duration_ms)
            
            # Handle errors
            if http_response.status_code >= 400:
                self._handle_response_error(http_response, request)
            
            return http_response
            
        except requests.exceptions.Timeout:
            raise NetworkError(
                f"Request timeout after {request.timeout}s",
                url=request.url,
                method=request.method.value
            )
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                f"Connection error: {e}",
                url=request.url,
                method=request.method.value
            )
        except requests.exceptions.RequestException as e:
            raise NetworkError(
                f"Network error: {e}",
                url=request.url,
                method=request.method.value
            )
    
    def make_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Make HTTP request with circuit breaker and performance monitoring.
        
        Args:
            request: HTTP request configuration
            
        Returns:
            HTTPResponse: Response object
            
        Raises:
            NetworkError: If network request fails
            AuthenticationError: If authentication fails
            FHIRServerError: If server returns error
            CircuitBreakerOpenError: If circuit breaker is open
        """
        self.request_count += 1
        
        # Apply circuit breaker if enabled
        if self.circuit_breaker:
            request_func = self.circuit_breaker(self._make_request_impl)
        else:
            request_func = self._make_request_impl
        
        # Apply performance monitoring if enabled
        if self.performance_monitor:
            operation_name = f"{request.method.value} {request.url}"
            monitored_func = self.performance_monitor.measure(operation_name)(request_func)
        else:
            monitored_func = request_func
        
        try:
            response = monitored_func(request)
            return response
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Request failed: {e}")
            raise
    
    def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make GET request."""
        from .models import HTTPMethod
        
        request = HTTPRequest(
            method=HTTPMethod.GET,
            url=url,
            headers=headers or {},
            params=params or {},
            timeout=timeout or self.server_config.timeout,
            verify_ssl=self.server_config.verify_ssl
        )
        return self.make_request(request)
    
    def post(
        self, 
        url: str, 
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make POST request."""
        from .models import HTTPMethod
        
        request = HTTPRequest(
            method=HTTPMethod.POST,
            url=url,
            headers=headers or {},
            params=params or {},
            data=data,
            timeout=timeout or self.server_config.timeout,
            verify_ssl=self.server_config.verify_ssl
        )
        return self.make_request(request)
    
    def put(
        self, 
        url: str, 
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make PUT request."""
        from .models import HTTPMethod
        
        request = HTTPRequest(
            method=HTTPMethod.PUT,
            url=url,
            headers=headers or {},
            params=params or {},
            data=data,
            timeout=timeout or self.server_config.timeout,
            verify_ssl=self.server_config.verify_ssl
        )
        return self.make_request(request)
    
    def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> HTTPResponse:
        """Make DELETE request."""
        from .models import HTTPMethod
        
        request = HTTPRequest(
            method=HTTPMethod.DELETE,
            url=url,
            headers=headers or {},
            params=params or {},
            timeout=timeout or self.server_config.timeout,
            verify_ssl=self.server_config.verify_ssl
        )
        return self.make_request(request)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'circuit_breaker_state': None,
            'performance_metrics': []
        }
        
        if self.circuit_breaker:
            stats['circuit_breaker_state'] = self.circuit_breaker.state
        
        if self.performance_monitor:
            stats['performance_metrics'] = self.performance_monitor.get_metrics()
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset client statistics."""
        self.request_count = 0
        self.error_count = 0
        
        if self.performance_monitor:
            self.performance_monitor.clear_metrics()
    
    def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self.session:
            self.session.close()
        
        self.logger.info(f"HTTP client closed. Total requests: {self.request_count}, Errors: {self.error_count}")


# Convenience functions for quick HTTP operations
def create_fhir_client(
    server_config: FHIRServerConfig,
    retry_config: Optional[RetryConfig] = None
) -> EnhancedHTTPClient:
    """
    Create HTTP client optimized for FHIR operations.
    
    Args:
        server_config: FHIR server configuration
        retry_config: Optional retry configuration
        
    Returns:
        EnhancedHTTPClient: Configured HTTP client
    """
    # Set FHIR-specific headers
    fhir_headers = {
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/fhir+json',
        **server_config.headers
    }
    
    server_config.headers = fhir_headers
    
    return EnhancedHTTPClient(
        server_config=server_config,
        retry_config=retry_config,
        enable_circuit_breaker=True,
        enable_performance_monitoring=True
    )


def make_fhir_request(
    method: str,
    url: str,
    server_config: FHIRServerConfig,
    auth_headers: Optional[Dict[str, str]] = None,
    data: Optional[Union[str, Dict[str, Any]]] = None,
    params: Optional[Dict[str, Any]] = None
) -> HTTPResponse:
    """
    Make a FHIR request with automatic client management.
    
    Args:
        method: HTTP method
        url: Request URL
        server_config: Server configuration
        auth_headers: Authentication headers
        data: Request data
        params: URL parameters
        
    Returns:
        HTTPResponse: Response object
    """
    client = create_fhir_client(server_config)
    
    try:
        headers = auth_headers or {}
        
        if method.upper() == 'GET':
            return client.get(url, headers=headers, params=params)
        elif method.upper() == 'POST':
            return client.post(url, data=data, headers=headers, params=params)
        elif method.upper() == 'PUT':
            return client.put(url, data=data, headers=headers, params=params)
        elif method.upper() == 'DELETE':
            return client.delete(url, headers=headers, params=params)
        else:
            from .models import HTTPMethod
            request = HTTPRequest(
                method=HTTPMethod[method.upper()],
                url=url,
                headers=headers,
                params=params or {},
                data=data,
                timeout=server_config.timeout,
                verify_ssl=server_config.verify_ssl
            )
            return client.make_request(request)
    finally:
        client.close() 