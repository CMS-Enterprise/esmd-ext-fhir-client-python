"""
Unit tests for ConfigUtility in esmd_shared.config module.
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
from esmd_shared.config import ConfigUtility


class TestConfigUtility:
    """Test cases for ConfigUtility class."""
    
    def test_init_with_config_file(self, temp_config_file):
        """Test ConfigUtility initialization with a config file."""
        config = ConfigUtility(config_file=temp_config_file)
        assert config.config_file == temp_config_file
        assert config.config is not None
        assert 'server' in config.config
        assert 'auth' in config.config
    
    def test_init_without_config_file(self):
        """Test ConfigUtility initialization without specifying config file."""
        with patch.object(ConfigUtility, '_find_config_file', return_value=None):
            config = ConfigUtility()
            assert config.config == {}
    
    def test_find_config_file_in_current_dir(self, tmp_path):
        """Test finding config file in current directory."""
        # Create config file in temporary directory
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")
        
        # Change to temporary directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = ConfigUtility()
            found_file = config._find_config_file()
            assert found_file == str(config_file)
        finally:
            os.chdir(original_cwd)
    
    def test_find_config_file_in_parent_dir(self, tmp_path):
        """Test finding config file in parent directory."""
        # Create config file in parent directory
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test: value")
        
        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        # Change to subdirectory
        original_cwd = os.getcwd()
        try:
            os.chdir(subdir)
            config = ConfigUtility()
            found_file = config._find_config_file()
            assert found_file == str(config_file)
        finally:
            os.chdir(original_cwd)
    
    def test_find_config_file_not_found(self, tmp_path):
        """Test when config file is not found."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = ConfigUtility()
            found_file = config._find_config_file()
            assert found_file is None
        finally:
            os.chdir(original_cwd)
    
    def test_load_config_success(self, temp_config_file):
        """Test successful config loading."""
        config = ConfigUtility(config_file=temp_config_file)
        assert config.config['server']['base_url'] == "http://test-server:9012/fhir"
        assert config.config['auth']['client_id'] == "test_client_id"
    
    def test_load_config_file_not_found(self, caplog):
        """Test config loading when file doesn't exist."""
        config = ConfigUtility(config_file="nonexistent.yaml")
        assert config.config == {}
        assert "Configuration file not found" in caplog.text
    
    def test_load_config_invalid_yaml(self, tmp_path, caplog):
        """Test config loading with invalid YAML."""
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content: [")
        
        config = ConfigUtility(config_file=str(invalid_config))
        assert config.config == {}
        assert "Error parsing YAML config file" in caplog.text
    
    def test_get_nested_value_success(self, temp_config_file):
        """Test getting nested configuration values."""
        config = ConfigUtility(config_file=temp_config_file)
        
        value = config._get_nested_value(['server', 'base_url'])
        assert value == "http://test-server:9012/fhir"
        
        value = config._get_nested_value(['auth', 'client_id'])
        assert value == "test_client_id"
    
    def test_get_nested_value_missing_key(self, temp_config_file):
        """Test getting nested value with missing key."""
        config = ConfigUtility(config_file=temp_config_file)
        
        value = config._get_nested_value(['nonexistent', 'key'], 'default')
        assert value == 'default'
        
        value = config._get_nested_value(['server', 'nonexistent'], 'default')
        assert value == 'default'
    
    def test_get_env_or_config_env_priority(self, temp_config_file):
        """Test that environment variables take priority over config."""
        with patch.dict(os.environ, {'TEST_VAR': 'env_value'}):
            config = ConfigUtility(config_file=temp_config_file)
            
            value = config._get_env_or_config('TEST_VAR', ['auth', 'client_id'], 'default')
            assert value == 'env_value'
    
    def test_get_env_or_config_config_fallback(self, temp_config_file):
        """Test fallback to config when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigUtility(config_file=temp_config_file)
            
            value = config._get_env_or_config('MISSING_VAR', ['auth', 'client_id'], 'default')
            assert value == 'test_client_id'
    
    def test_get_env_or_config_default_fallback(self, temp_config_file):
        """Test fallback to default when neither env nor config available."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigUtility(config_file=temp_config_file)
            
            value = config._get_env_or_config('MISSING_VAR', ['missing', 'key'], 'default')
            assert value == 'default'
    
    def test_get_fhir_server_url(self, temp_config_file):
        """Test getting FHIR server URL."""
        config = ConfigUtility(config_file=temp_config_file)
        url = config.get_fhir_server_url()
        assert url == "http://test-server:9012/fhir"
    
    def test_get_fhir_server_url_from_env(self, temp_config_file):
        """Test getting FHIR server URL from environment."""
        with patch.dict(os.environ, {'ESMD_FHIR_SERVER_URL': 'http://env-server:8080/fhir'}):
            config = ConfigUtility(config_file=temp_config_file)
            url = config.get_fhir_server_url()
            assert url == 'http://env-server:8080/fhir'
    
    def test_get_presigned_url_base(self, temp_config_file):
        """Test getting presigned URL base."""
        config = ConfigUtility(config_file=temp_config_file)
        url = config.get_presigned_url_base()
        assert url == "http://test-server:9016/fhir"
    
    def test_get_timeout_valid_int(self, temp_config_file):
        """Test getting timeout as valid integer."""
        config = ConfigUtility(config_file=temp_config_file)
        timeout = config.get_timeout()
        assert timeout == 30
        assert isinstance(timeout, int)
    
    def test_get_timeout_invalid_value(self, caplog):
        """Test getting timeout with invalid value."""
        with patch.dict(os.environ, {'ESMD_TIMEOUT': 'invalid'}):
            config = ConfigUtility()
            timeout = config.get_timeout()
            assert timeout == 30  # default value
            assert "Invalid timeout value" in caplog.text
    
    def test_get_token_endpoint(self, temp_config_file):
        """Test getting token endpoint."""
        config = ConfigUtility(config_file=temp_config_file)
        endpoint = config.get_token_endpoint()
        assert endpoint == "https://test.example.com/auth/token"
    
    def test_get_client_id(self, temp_config_file):
        """Test getting client ID."""
        config = ConfigUtility(config_file=temp_config_file)
        client_id = config.get_client_id()
        assert client_id == "test_client_id"
    
    def test_get_client_secret_from_env(self, temp_config_file):
        """Test getting client secret from environment (preferred)."""
        with patch.dict(os.environ, {'ESMD_CLIENT_SECRET': 'env_secret'}):
            config = ConfigUtility(config_file=temp_config_file)
            secret = config.get_client_secret()
            assert secret == 'env_secret'
    
    def test_get_client_secret_from_config(self, temp_config_file, caplog):
        """Test getting client secret from config file (with warning)."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigUtility(config_file=temp_config_file)
            secret = config.get_client_secret()
            assert secret == "test_client_secret"
            assert "Using client secret from config file" in caplog.text
    
    def test_get_client_secret_missing(self):
        """Test getting client secret when not available."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigUtility()
            secret = config.get_client_secret()
            assert secret == ''
    
    def test_get_scope(self, temp_config_file):
        """Test getting OAuth scope."""
        config = ConfigUtility(config_file=temp_config_file)
        scope = config.get_scope()
        assert scope == "test_scope"
    
    def test_get_auth_token(self):
        """Test getting auth token from environment."""
        with patch.dict(os.environ, {'ESMD_ACCESS_TOKEN': 'test_token'}):
            config = ConfigUtility()
            token = config.get_auth_token()
            assert token == 'test_token'
    
    def test_get_auth_token_missing(self):
        """Test getting auth token when not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigUtility()
            token = config.get_auth_token()
            assert token is None
    
    def test_get_oid(self, temp_config_file):
        """Test getting organization OID."""
        config = ConfigUtility(config_file=temp_config_file)
        oid = config.get_oid()
        assert oid == "urn:oid:1.2.3.4.5"
    
    def test_get_org_name(self, temp_config_file):
        """Test getting organization name."""
        config = ConfigUtility(config_file=temp_config_file)
        name = config.get_org_name()
        assert name == "Test Organization"
    
    def test_get_logging_level(self, temp_config_file):
        """Test getting logging level."""
        config = ConfigUtility(config_file=temp_config_file)
        level = config.get_logging_level()
        assert level == "DEBUG"
    
    def test_get_log_file(self, temp_config_file):
        """Test getting log file path."""
        config = ConfigUtility(config_file=temp_config_file)
        log_file = config.get_log_file()
        assert log_file == "test.log"
    
    def test_get_all_config(self, temp_config_file):
        """Test getting complete configuration dictionary."""
        config = ConfigUtility(config_file=temp_config_file)
        all_config = config.get_all_config()
        
        assert isinstance(all_config, dict)
        assert 'server' in all_config
        assert 'auth' in all_config
        assert all_config is not config.config  # Should be a copy
    
    def test_validate_required_config_success(self, temp_config_file):
        """Test configuration validation with all required fields."""
        with patch.dict(os.environ, {'ESMD_CLIENT_SECRET': 'test_secret'}):
            config = ConfigUtility(config_file=temp_config_file)
            assert config.validate_required_config() is True
    
    def test_validate_required_config_missing_server_url(self, caplog):
        """Test configuration validation with missing server URL."""
        config = ConfigUtility()
        with patch.object(config, 'get_fhir_server_url', return_value=''):
            assert config.validate_required_config() is False
            assert "Required configuration missing: FHIR Server URL" in caplog.text
    
    def test_validate_required_config_missing_client_id(self, temp_config_file, caplog):
        """Test configuration validation with missing client ID."""
        config = ConfigUtility(config_file=temp_config_file)
        with patch.object(config, 'get_client_id', return_value=''):
            assert config.validate_required_config() is False
            assert "Required configuration missing: Client ID" in caplog.text
    
    def test_validate_required_config_missing_client_secret(self, temp_config_file, caplog):
        """Test configuration validation with missing client secret."""
        config = ConfigUtility(config_file=temp_config_file)
        with patch.object(config, 'get_client_secret', return_value=''):
            assert config.validate_required_config() is False
            assert "Required configuration missing: Client Secret" in caplog.text
    
    def test_validate_required_config_whitespace_values(self, temp_config_file, caplog):
        """Test configuration validation with whitespace-only values."""
        config = ConfigUtility(config_file=temp_config_file)
        with patch.object(config, 'get_client_secret', return_value='   '):
            assert config.validate_required_config() is False
            assert "Required configuration missing: Client Secret" in caplog.text


@pytest.mark.integration
class TestConfigUtilityIntegration:
    """Integration tests for ConfigUtility with real files."""
    
    def test_real_config_file_loading(self, tmp_path):
        """Test loading a real config file."""
        config_content = {
            'server': {
                'base_url': 'http://integration-test:9012/fhir',
                'timeout': 45
            },
            'auth': {
                'client_id': 'integration_client',
                'scope': 'integration_scope'
            }
        }
        
        config_file = tmp_path / "integration_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        config = ConfigUtility(config_file=str(config_file))
        
        assert config.get_fhir_server_url() == 'http://integration-test:9012/fhir'
        assert config.get_timeout() == 45
        assert config.get_client_id() == 'integration_client'
        assert config.get_scope() == 'integration_scope'
    
    def test_environment_override_integration(self, temp_config_file):
        """Test that environment variables properly override config file."""
        env_vars = {
            'ESMD_FHIR_SERVER_URL': 'http://env-override:8080/fhir',
            'ESMD_CLIENT_ID': 'env_client_id',
            'ESMD_TIMEOUT': '60',
            'ESMD_LOG_LEVEL': 'ERROR'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ConfigUtility(config_file=temp_config_file)
            
            assert config.get_fhir_server_url() == 'http://env-override:8080/fhir'
            assert config.get_client_id() == 'env_client_id'
            assert config.get_timeout() == 60
            assert config.get_logging_level() == 'ERROR'
            
            # Values not overridden should come from config file
            assert config.get_scope() == 'test_scope'
            assert config.get_oid() == 'urn:oid:1.2.3.4.5' 