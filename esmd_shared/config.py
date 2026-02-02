"""
Enhanced Configuration Utility for EsmdFHIRClient.

This module provides robust configuration management with environment variable
support, validation, caching, and improved error handling.
"""

import os
import yaml
from typing import Optional, Dict, Any, Union, List, Type, TypeVar
import logging
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

from esmd_shared.models import ValidationResult, FHIRServerConfig, AuthConfig, LoggerConfig
from esmd_shared.exceptions import ConfigurationError, ValidationError, FileOperationError
from esmd_shared.utils import (
    validate_required_fields, validate_url, validate_file_path,
    safe_json_extract
)

T = TypeVar('T')


class ConfigUtility:
    """
    Advanced configuration utility for managing application settings.
    
    Features:
    - YAML configuration files with environment variable overrides
    - Validation and type conversion
    - Configuration caching for performance
    - Secure credential handling
    - Auto-discovery of config files
    """
    
    def __init__(self, config_file: Optional[str] = None, enable_caching: bool = True, load_env: bool = True):
        """
        Initialize the ConfigUtility.
        
        Args:
            config_file: Path to YAML config file. If None, searches for config.yaml
            enable_caching: Whether to enable configuration value caching
            load_env: Whether to load environment variables from .env file
            
        Raises:
            ConfigurationError: If config file is specified but doesn't exist
            FileOperationError: If config file cannot be read
        """
        self.logger = logging.getLogger(__name__)
        self.config: Dict[str, Any] = {}
        self.enable_caching = enable_caching
        self._config_cache: Dict[str, Any] = {}
        
        # Load environment variables from .env file if requested
        if load_env:
            self._load_env_file()
        
        # Validate and load configuration file
        if config_file:
            if not Path(config_file).exists():
                raise ConfigurationError(
                    f"Specified config file does not exist: {config_file}",
                    missing_keys=["config_file"]
                )
            self.config_file = config_file
        else:
            self.config_file = self._find_config_file()
        
        self._load_config()
        self._validate_core_config()
    
    def _load_env_file(self) -> None:
        """
        Load environment variables from .env file.
        
        This method will look for a .env file in the current directory
        and load all environment variables from it.
        """
        env_file = Path('.env')
        if env_file.exists():
            try:
                load_dotenv(env_file)
                self.logger.info(f"Loaded environment variables from {env_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load .env file: {e}")
        else:
            self.logger.info("No .env file found, using system environment variables")
    
    def _find_config_file(self) -> Optional[str]:
        """
        Find config.yaml file in current directory or parent directories.
        
        Returns:
            Optional[str]: Path to config file if found, None otherwise.
        """
        current_dir = Path.cwd()
        config_filenames = ['config.yaml', 'config.yml', '.config.yaml']
        
        # Search current directory and up to 4 parent directories
        for _ in range(5):
            for filename in config_filenames:
                config_path = current_dir / filename
                if config_path.exists() and config_path.is_file():
                    self.logger.info(f"Found config file: {config_path}")
                    return str(config_path)
            
            if current_dir.parent == current_dir:  # Reached root
                break
            current_dir = current_dir.parent
            
        self.logger.info("No config file found, will use environment variables and defaults")
        return None
    
    def _load_config(self) -> None:
        """
        Load configuration from YAML file with comprehensive error handling.
        
        Raises:
            FileOperationError: If file cannot be read
            ConfigurationError: If YAML is invalid
        """
        if not self.config_file:
            self.logger.info("No config file specified, using environment variables only")
            self.config = {}
            return
        
        try:
            config_path = Path(self.config_file)
            
            # Validate file access
            if not config_path.exists():
                raise FileOperationError(
                    f"Configuration file not found: {self.config_file}",
                    file_path=self.config_file,
                    operation="read"
                )
            
            if not os.access(self.config_file, os.R_OK):
                raise FileOperationError(
                    f"Configuration file is not readable: {self.config_file}",
                    file_path=self.config_file,
                    operation="read"
                )
            
            # Load and parse YAML
            with open(self.config_file, 'r', encoding='utf-8') as file:
                content = file.read()
                if not content.strip():
                    self.logger.warning(f"Configuration file is empty: {self.config_file}")
                    self.config = {}
                    return
                
                self.config = yaml.safe_load(content) or {}
                
            self.logger.info(f"Configuration loaded successfully from {self.config_file}")
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file {self.config_file}: {e}"
            )
        except PermissionError:
            raise FileOperationError(
                f"Permission denied reading configuration file: {self.config_file}",
                file_path=self.config_file,
                operation="read"
            )
        except Exception as e:
            raise FileOperationError(
                f"Unexpected error reading configuration file {self.config_file}: {e}",
                file_path=self.config_file,
                operation="read"
            )
    
    def _validate_core_config(self) -> None:
        """Validate core configuration after loading."""
        if self.config_file:
            # Validate config file structure
            if not isinstance(self.config, dict):
                raise ConfigurationError("Configuration file must contain a valid YAML dictionary")
    
    def _get_nested_value(self, keys: List[str], default: Any = None) -> Any:
        """
        Get nested value from config dictionary with validation.
        
        Args:
            keys: List of nested keys (e.g., ['server', 'base_url'])
            default: Default value if key not found
            
        Returns:
            Any: Configuration value or default
            
        Raises:
            ValidationError: If keys parameter is invalid
        """
        if not keys:
            raise ValidationError("Keys parameter cannot be empty", field="keys", value=keys)
        
        if not isinstance(keys, list):
            raise ValidationError("Keys must be a list", field="keys", value=keys)
        
        try:
            value = self.config
            for key in keys:
                if not isinstance(value, dict):
                    return default
                value = value.get(key)
                if value is None:
                    return default
            return value
        except (KeyError, TypeError, AttributeError):
            return default
    
    @lru_cache(maxsize=128)
    def _get_env_or_config_cached(
        self, 
        env_var: str, 
        config_keys_str: str, 
        default: str = ""
    ) -> str:
        """Cached version of _get_env_or_config for string values."""
        config_keys = config_keys_str.split('.')
        return self._get_env_or_config(env_var, config_keys, default)
    
    def _get_env_or_config(
        self, 
        env_var: str, 
        config_keys: List[str], 
        default: Any = None,
        required: bool = False,
        value_type: Type = str
    ) -> Any:
        """
        Get value from environment variable first, then config file, then default.
        
        Args:
            env_var: Environment variable name
            config_keys: List of nested config keys
            default: Default value
            required: Whether the value is required
            value_type: Expected type for conversion
            
        Returns:
            Any: Configuration value with proper type
            
        Raises:
            ConfigurationError: If required value is missing
            ValidationError: If type conversion fails
        """
        # Try environment variable first
        env_value = os.getenv(env_var)
        if env_value is not None:
            return self._convert_type(env_value, value_type, f"environment variable {env_var}")
        
        # Try config file
        config_value = self._get_nested_value(config_keys)
        if config_value is not None:
            return self._convert_type(config_value, value_type, f"config key {'.'.join(config_keys)}")
        
        # Use default or raise if required
        if required and default is None:
            raise ConfigurationError(
                f"Required configuration missing: {env_var} (or config path: {'.'.join(config_keys)})",
                missing_keys=[env_var]
            )
        
        if default is not None:
            return self._convert_type(default, value_type, "default value")
        
        return default
    
    def _convert_type(self, value: Any, target_type: Type, source: str) -> Any:
        """
        Convert value to target type with validation.
        
        Args:
            value: Value to convert
            target_type: Target type
            source: Source description for error messages
            
        Returns:
            Any: Converted value
            
        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return None
        
        if isinstance(value, target_type):
            return value
        
        try:
            if target_type == bool:
                if isinstance(value, str):
                    return str(value).lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif target_type == int:
                return int(value)
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return str(value)
            else:
                return target_type(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Cannot convert {source} value '{value}' to {target_type.__name__}: {e}",
                field=source,
                value=value
            )
    
    # Server Configuration Methods
    def get_fhir_server_url(self) -> str:
        """
        Get FHIR Server Base URL from config or environment.
        
        Returns:
            str: FHIR server URL
            
        Raises:
            ConfigurationError: If URL is missing or invalid
        """
        url = self._get_env_or_config(
            'ESMD_FHIR_SERVER_URL',
            ['server', 'base_url'],
            'http://localhost:8080/fhir',
            required=True
        )
        
        # Validate URL format
        validation = validate_url(url)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid FHIR server URL: {url}. {', '.join(validation.errors)}",
                field="fhir_server_url",
                value=url
            )
        
        return url
    
    # Server Configuration Methods
    def get_fhir_terminology_server_url(self) -> str:
        """
        Get FHIR Terminology Server URL from config or environment.

        Returns:
            str: FHIR Terminology server URL
        """
        url = self._get_env_or_config(
            'ESMD_FHIR_TERMINOLOGY_URL',
            ['server', 'terminology_url'],
            'http://localhost:8080/fhir/terminology',
            required=True
        )

        # Validate URL format
        validation = validate_url(url)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid FHIR Terminology server URL: {url}. {', '.join(validation.errors)}",
                field="fhir_terminology_server_url",
                value=url
            )

        return url        
        


    def get_presigned_url_base(self) -> str:
        """Get Presigned URL Base from config or environment."""
        url = self._get_env_or_config(
            'ESMD_PRESIGNED_URL_BASE',
            ['server', 'presigned_base_url'],
            self.get_fhir_server_url()
        )
        
        # Validate URL format
        validation = validate_url(url)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid presigned URL base: {url}. {', '.join(validation.errors)}",
                field="presigned_url_base",
                value=url
            )
        
        return url
    
    def get_timeout(self) -> int:
        """
        Get server timeout from config or environment.
        
        Returns:
            int: Timeout in seconds (1-300 range)
            
        Raises:
            ValidationError: If timeout is invalid
        """
        timeout = self._get_env_or_config(
            'ESMD_TIMEOUT',
            ['server', 'timeout'],
            30,
            value_type=int
        )
        
        # Validate timeout range
        if not (1 <= timeout <= 300):
            raise ValidationError(
                f"Timeout must be between 1 and 300 seconds, got: {timeout}",
                field="timeout",
                value=timeout
            )
        
        return timeout
    
    def get_verify_ssl(self) -> bool:
        """Get SSL verification setting from config or environment."""
        return self._get_env_or_config(
            'ESMD_VERIFY_SSL',
            ['server', 'verify_ssl'],
            True,
            value_type=bool
        )
    
    # Authentication Configuration Methods
    def get_token_endpoint(self) -> str:
        """
        Get token endpoint from config or environment.
        
        Returns:
            str: Token endpoint URL
            
        Raises:
            ConfigurationError: If endpoint is missing
            ValidationError: If URL is invalid
        """
        url = self._get_env_or_config(
            'ESMD_TOKEN_ENDPOINT',
            ['auth', 'token_endpoint'],
            required=True
        )
        
        # Validate URL format
        validation = validate_url(url)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid token endpoint URL: {url}. {', '.join(validation.errors)}",
                field="token_endpoint",
                value=url
            )
        
        return url
    
    def get_client_id(self) -> str:
        """
        Get client ID from config or environment.
        
        Returns:
            str: Client ID
            
        Raises:
            ConfigurationError: If client ID is missing
        """
        client_id = self._get_env_or_config(
            'ESMD_CLIENT_ID',
            ['auth', 'client_id'],
            required=True
        )
        
        if not client_id.strip():
            raise ConfigurationError(
                "Client ID cannot be empty",
                missing_keys=["ESMD_CLIENT_ID"]
            )
        
        return client_id
    
    def get_client_secret(self) -> str:
        """
        Get client secret from environment (recommended) or config.
        
        Returns:
            str: Client secret
            
        Raises:
            ConfigurationError: If client secret is missing
        """
        # Prefer environment variable for security
        secret = os.getenv('ESMD_CLIENT_SECRET')
        if secret:
            if not secret.strip():
                raise ConfigurationError(
                    "Client secret cannot be empty",
                    missing_keys=["ESMD_CLIENT_SECRET"]
                )
            return secret
        
        # Fallback to config file (less secure)
        config_secret = self._get_nested_value(['auth', 'client_secret'])
        if config_secret:
            self.logger.warning(
                "Using client secret from config file. "
                "Consider using ESMD_CLIENT_SECRET environment variable for better security."
            )
            if not str(config_secret).strip():
                raise ConfigurationError(
                    "Client secret cannot be empty",
                    missing_keys=["client_secret"]
                )
            return str(config_secret)
        
        raise ConfigurationError(
            "Client secret is required but not found in environment or config",
            missing_keys=["ESMD_CLIENT_SECRET", "auth.client_secret"]
        )
    
    def get_scope(self) -> str:
        """Get OAuth scope from config or environment."""
        return self._get_env_or_config(
            'ESMD_SCOPE',
            ['auth', 'scope'],
            'read'
        )
    
    def get_auth_token(self) -> Optional[str]:
        """Get pre-existing auth token from environment."""
        token = os.getenv('ESMD_ACCESS_TOKEN')
        if token and not token.strip():
            self.logger.warning("Access token is empty")
            return None
        return token
    
    # Organization Configuration Methods
    def get_oid(self) -> str:
        """Get organization OID from config or environment."""
        oid = self._get_env_or_config(
            'ESMD_ORG_OID',
            ['org', 'oid'],
            'urn:oid:1.2.3.4'
        )
        
        # Basic OID validation
        if not oid.startswith('urn:oid:') or len(oid.split('.')) < 3:
            self.logger.warning(f"OID may be invalid: {oid}")
        
        return oid
    
    def get_org_name(self) -> str:
        """Get organization name from config or environment."""
        return self._get_env_or_config(
            'ESMD_ORG_NAME',
            ['org', 'name'],
            'Default Organization'
        )
    
    # Logging Configuration Methods
    def get_logging_level(self) -> str:
        """Get logging level from config or environment."""
        level = self._get_env_or_config(
            'ESMD_LOG_LEVEL',
            ['logging', 'level'],
            'INFO'
        ).upper()
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            self.logger.warning(f"Invalid log level '{level}', using INFO")
            return 'INFO'
        
        return level
    
    def get_log_file(self) -> Optional[str]:
        """Get log file path from config or environment."""
        log_file = self._get_env_or_config(
            'ESMD_LOG_FILE',
            ['logging', 'log_file'],
            None
        )
        
        if log_file:
            # Validate file path
            validation = validate_file_path(log_file)
            if not validation.is_valid:
                self.logger.warning(f"Invalid log file path: {log_file}")
                return None
        
        return log_file
    
    # Advanced Configuration Methods
    def get_fhir_server_config(self) -> FHIRServerConfig:
        """Get complete FHIR server configuration."""
        return FHIRServerConfig(
            base_url=self.get_fhir_server_url(),
            timeout=self.get_timeout(),
            verify_ssl=self.get_verify_ssl(),
            headers=self._get_nested_value(['server', 'headers'], {})
        )
    
    def get_auth_config(self) -> AuthConfig:
        """Get complete authentication configuration."""
        return AuthConfig(
            client_id=self.get_client_id(),
            client_secret=self.get_client_secret(),
            token_endpoint=self.get_token_endpoint(),
            scope=self.get_scope(),
            timeout=self.get_timeout()
        )
    
    def get_logger_config(self, name: str) -> LoggerConfig:
        """Get logger configuration."""
        return LoggerConfig(
            name=name,
            level=self.get_logging_level(),
            file_path=self.get_log_file(),
            console_logging=self._get_env_or_config(
                'ESMD_CONSOLE_LOGGING',
                ['logging', 'console'],
                True,
                value_type=bool
            )
        )
    
    # Utility Methods
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary (excluding sensitive data).
        
        Returns:
            Dict[str, Any]: Complete configuration dictionary
        """
        safe_config = {}
        
        # Server config
        try:
            safe_config['server'] = {
                'base_url': self.get_fhir_server_url(),
                'presigned_base_url': self.get_presigned_url_base(),
                'timeout': self.get_timeout(),
                'verify_ssl': self.get_verify_ssl()
            }
        except Exception:
            safe_config['server'] = {'error': 'Failed to load server config'}
        
        # Auth config (without secrets)
        try:
            safe_config['auth'] = {
                'token_endpoint': self.get_token_endpoint(),
                'client_id': self.get_client_id(),
                'scope': self.get_scope(),
                'has_client_secret': bool(self.get_client_secret()),
                'has_access_token': bool(self.get_auth_token())
            }
        except Exception:
            safe_config['auth'] = {'error': 'Failed to load auth config'}
        
        # Org config
        try:
            safe_config['org'] = {
                'oid': self.get_oid(),
                'name': self.get_org_name()
            }
        except Exception:
            safe_config['org'] = {'error': 'Failed to load org config'}
        
        # Logging config
        try:
            safe_config['logging'] = {
                'level': self.get_logging_level(),
                'log_file': self.get_log_file()
            }
        except Exception:
            safe_config['logging'] = {'error': 'Failed to load logging config'}
        
        return safe_config
    
    def validate_configuration(self) -> ValidationResult:
        """
        Validate complete configuration.
        
        Returns:
            ValidationResult: Comprehensive validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Test critical configuration values
        critical_tests = [
            ('FHIR Server URL', self.get_fhir_server_url),
            ('Token Endpoint', self.get_token_endpoint),
            ('Client ID', self.get_client_id),
            ('Client Secret', self.get_client_secret),
        ]
        
        for name, getter in critical_tests:
            try:
                value = getter()
                if not value or (isinstance(value, str) and not value.strip()):
                    result.errors.append(f"Required configuration missing or empty: {name}")
            except Exception as e:
                result.errors.append(f"Error validating {name}: {str(e)}")
        
        # Test optional configuration with warnings
        optional_tests = [
            ('Organization OID', self.get_oid),
            ('Organization Name', self.get_org_name),
            ('Timeout', self.get_timeout),
        ]
        
        for name, getter in optional_tests:
            try:
                getter()
            except Exception as e:
                result.warnings.append(f"Warning in {name}: {str(e)}")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def reload_config(self) -> None:
        """
        Reload configuration from file and clear cache.
        
        Raises:
            ConfigurationError: If reload fails
        """
        if self.enable_caching:
            self._get_env_or_config_cached.cache_clear()
        
        self._config_cache.clear()
        self._load_config()
        self._validate_core_config()
        self.logger.info("Configuration reloaded successfully")
    
    def set_config_value(self, keys: List[str], value: Any) -> None:
        """
        Set a configuration value programmatically (runtime only).
        
        Args:
            keys: List of nested keys
            value: Value to set
            
        Raises:
            ValidationError: If keys are invalid
        """
        if not keys:
            raise ValidationError("Keys cannot be empty", field="keys", value=keys)
        
        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        
        # Clear cache if enabled
        if self.enable_caching:
            self._get_env_or_config_cached.cache_clear()
        
        self.logger.debug(f"Set config value: {'.'.join(keys)} = {value}")
    
    def has_config_file(self) -> bool:
        """Check if a configuration file is loaded."""
        return self.config_file is not None 