"""
Unit tests for logger module in esmd_shared.logger.
"""

import pytest
import logging
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from esmd_shared.logger import (
    setup_logger, 
    get_log_level, 
    create_formatter,
    configure_root_logger,
    get_logger_info
)


class TestSetupLogger:
    """Test cases for setup_logger function."""
    
    def test_setup_logger_basic(self):
        """Test basic logger setup."""
        logger = setup_logger("test_logger")
        
        print(f"logger, {logger}")
        assert logger.__getattr__("name") == "test_logger"        
        assert logger.level == logging.INFO  # Default level        
        assert len(logger.handlers) >= 1  # Should have at least console handler
    
    def test_setup_logger_custom_level(self):
        """Test logger setup with custom level."""
        os.environ['ESMD_LOG_LEVEL'] = 'DEBUG'
        logger = setup_logger("test_logger")
        assert logger.level == logging.DEBUG
        # Ensure all handlers are set to DEBUG
        for handler in logger.handlers:
            assert handler.level == logging.DEBUG, f"Handler {handler} level is {logging.getLevelName(handler.level)} instead of DEBUG"
        del os.environ['ESMD_LOG_LEVEL']


    def test_setup_logger_with_file(self, tmp_path):
        """Test logger setup with file handler."""
        log_file = tmp_path / "test.log"
        os.environ['ESMD_LOG_FILE'] = str(log_file)
        logger = setup_logger("test_logger")
        assert len(logger.handlers) == 2
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        logger.info("Test message")
        assert log_file.exists()
        assert "Test message" in log_file.read_text()
        del os.environ['ESMD_LOG_FILE']

    def test_setup_logger_custom_format(self):
        """Test logger setup with custom format."""
        custom_format = "%(levelname)s: %(message)s"
        logger = setup_logger("test_logger", format_string=custom_format)
        
        # Check that formatter is applied
        handler = logger.handlers[0]
        assert handler.formatter._fmt == custom_format
    
    def test_setup_logger_file_creation_error(self, tmp_path, caplog):
        """Test logger setup when file creation fails."""
        # Try to create log file in non-existent directory with no permissions
        invalid_path = "/root/nonexistent/test.log"
        
        os.environ['ESMD_LOG_FILE'] = invalid_path
        logger = setup_logger("test_logger")
        assert logger is not None
        assert len(logger.handlers) >= 1
        assert "Could not create file handler" in caplog.text
        del os.environ['ESMD_LOG_FILE']
    
    def test_setup_logger_no_duplicate_handlers(self):
        """Test that multiple calls don't create duplicate handlers."""
        logger1 = setup_logger("duplicate_test")
        initial_handlers = len(logger1.handlers)
        
        logger2 = setup_logger("duplicate_test")  # Same name
        
        assert logger1 is logger2
        assert len(logger2.handlers) == initial_handlers
    
    def test_setup_logger_max_bytes_and_backup_count(self, tmp_path):
        """Test logger setup with custom rotation settings."""
        log_file = tmp_path / "rotating.log"
        os.environ['ESMD_LOG_FILE'] = str(log_file)
        os.environ['ESMD_LOG_MAX_BYTES'] = '1024'
        os.environ['ESMD_LOG_BACKUP_COUNT'] = '3'
        logger = setup_logger("rotating_logger")
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        file_handler = file_handlers[0]
        assert file_handler.maxBytes == 1024
        assert file_handler.backupCount == 3
        del os.environ['ESMD_LOG_FILE']
        del os.environ['ESMD_LOG_MAX_BYTES']
        del os.environ['ESMD_LOG_BACKUP_COUNT']


# class TestLogLevelFunction:
#     """Test cases for _get_log_level function."""
    
#     def test_get_log_level_valid_strings(self):
#         """Test _get_log_level with valid level strings."""
#         assert get_log_level("DEBUG") == logging.DEBUG
#         assert get_log_level("INFO") == logging.INFO
#         assert get_log_level("WARNING") == logging.WARNING
#         assert get_log_level("WARN") == logging.WARNING
#         assert get_log_level("ERROR") == logging.ERROR
#         assert get_log_level("CRITICAL") == logging.CRITICAL
#         assert get_log_level("FATAL") == logging.CRITICAL
    
#     def test_get_log_level_case_insensitive(self):
#         """Test _get_log_level is case insensitive."""
#         assert get_log_level("debug") == logging.DEBUG
#         assert get_log_level("Info") == logging.INFO
#         assert get_log_level("WARNING") == logging.WARNING
    
#     def test_get_log_level_invalid_string(self):
#         """Test _get_log_level with invalid level string."""
#         assert get_log_level("INVALID") == logging.INFO  # Default
#         assert get_log_level("") == logging.INFO
    
#     def test_get_log_level_none_uses_env(self):
#         """Test _get_log_level uses environment variable when level is None."""
#         with patch.dict(os.environ, {'ESMD_LOG_LEVEL': 'ERROR'}):
#             assert get_log_level(None) == logging.ERROR
    
#     def test_get_log_level_none_no_env(self):
#         """Test _get_log_level defaults to INFO when no level or env."""
#         with patch.dict(os.environ, {}, clear=True):
#             assert get_log_level(None) == logging.INFO


# class TestCreateFormatter:
#     """Test cases for _create_formatter function."""
    
#     def test_create_formatter_default(self):
#         """Test _create_formatter with default format."""
#         formatter = create_formatter()
        
#         assert isinstance(formatter, logging.Formatter)
#         expected_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
#         assert formatter._fmt == expected_format
#         assert formatter.datefmt == '%Y-%m-%d %H:%M:%S'
    
#     def test_create_formatter_custom(self):
#         """Test _create_formatter with custom format."""
#         custom_format = "%(levelname)s: %(message)s"
#         formatter = create_formatter(custom_format)
        
#         assert formatter._fmt == custom_format
#         assert formatter.datefmt == '%Y-%m-%d %H:%M:%S'
    
#     def test_create_formatter_none_format(self):
#         """Test _create_formatter with None format string."""
#         formatter = create_formatter(None)
        
#         expected_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
#         assert formatter._fmt == expected_format


# class TestConfigureRootLogger:
#     """Test cases for configure_root_logger function."""
    
#     def setup_method(self):
#         """Clear root logger handlers before each test."""
#         root_logger = logging.getLogger()
#         root_logger.handlers.clear()
    
#     def test_configure_root_logger_basic(self):
#         """Test basic root logger configuration."""
#         configure_root_logger()
        
#         root_logger = logging.getLogger()
#         assert root_logger.level == logging.INFO
    
#     def test_configure_root_logger_custom_level(self):
#         """Test root logger configuration with custom level."""
#         configure_root_logger(level="DEBUG")
        
#         root_logger = logging.getLogger()
#         assert root_logger.level == logging.DEBUG
    
#     def test_configure_root_logger_with_file(self, tmp_path):
#         """Test root logger configuration with file handler."""
#         log_file = tmp_path / "root.log"
#         configure_root_logger(log_file=str(log_file))
        
#         root_logger = logging.getLogger()
        
#         # Should have file handler added
#         file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
#         assert len(file_handlers) == 1
        
#         # Test logging
#         root_logger.info("Root test message")
#         assert log_file.exists()
#         assert "Root test message" in log_file.read_text()
    
#     def test_configure_root_logger_file_error(self, caplog):
#         """Test root logger configuration when file creation fails."""
#         invalid_path = "/root/nonexistent/root.log"
        
#         configure_root_logger(log_file=invalid_path)
        
#         # Should log warning about file handler failure
#         assert "Could not add file handler to root logger" in caplog.text
    
#     def test_configure_root_logger_disable_existing(self):
#         """Test root logger configuration with disable_existing=True."""
#         # Add a handler first
#         root_logger = logging.getLogger()
#         test_handler = logging.StreamHandler()
#         root_logger.addHandler(test_handler)
#         initial_count = len(root_logger.handlers)
        
#         configure_root_logger(disable_existing=True)
        
#         # Handlers should be cleared and new ones added
#         assert len(root_logger.handlers) >= 1
    
#     def test_configure_root_logger_keep_existing(self):
#         """Test root logger configuration with disable_existing=False."""
#         # Add a handler first
#         root_logger = logging.getLogger()
#         test_handler = logging.StreamHandler()
#         root_logger.addHandler(test_handler)
#         initial_count = len(root_logger.handlers)
        
#         configure_root_logger(disable_existing=False)
        
#         # Should keep existing handlers and add new ones
#         assert len(root_logger.handlers) >= initial_count


# class TestGetLoggerInfo:
#     """Test cases for get_logger_info function."""
    
#     def setup_method(self):
#         """Clear root logger handlers before each test."""
#         root_logger = logging.getLogger()
#         root_logger.handlers.clear()
    
#     def test_get_logger_info_basic(self):
#         """Test get_logger_info with basic configuration."""
#         configure_root_logger()
        
#         info = get_logger_info()
        
#         assert isinstance(info, dict)
#         assert 'root_level' in info
#         assert 'handlers' in info
#         assert 'loggers' in info
#         assert info['root_level'] == 'INFO'
    
#     def test_get_logger_info_with_file_handler(self, tmp_path):
#         """Test get_logger_info with file handler."""
#         log_file = tmp_path / "info_test.log"
#         configure_root_logger(log_file=str(log_file))
        
#         info = get_logger_info()
        
#         # Should have handlers including file handler
#         assert len(info['handlers']) >= 1
        
#         # Check for file handler info
#         file_handlers = [h for h in info['handlers'] if h['type'] == 'RotatingFileHandler']
#         assert len(file_handlers) == 1
#         assert 'file' in file_handlers[0]
    
#     def test_get_logger_info_with_custom_loggers(self):
#         """Test get_logger_info with custom loggers."""
#         # Create some custom loggers
#         logger1 = setup_logger("custom_logger_1", level="DEBUG")
#         logger2 = setup_logger("custom_logger_2", level="WARNING")
        
#         info = get_logger_info()
        
#         # Should include custom loggers
#         assert len(info['loggers']) >= 2
        
#         logger_names = [logger['name'] for logger in info['loggers']]
#         assert 'custom_logger_1' in logger_names
#         assert 'custom_logger_2' in logger_names


# class TestLoggerIntegration:
#     """Integration tests for logger functionality."""
    
#     def test_logger_hierarchy(self):
#         """Test logger hierarchy and inheritance."""
#         parent_logger = setup_logger("parent", level="DEBUG")
#         child_logger = setup_logger("parent.child")
        
#         # Child should inherit level from parent
#         assert child_logger.parent == parent_logger
    
#     def test_multiple_loggers_same_file(self, tmp_path):
#         """Test multiple loggers writing to the same file."""
#         log_file = tmp_path / "shared.log"
        
#         logger1 = setup_logger("logger1", log_file=str(log_file))
#         logger2 = setup_logger("logger2", log_file=str(log_file))
        
#         logger1.info("Message from logger1")
#         logger2.info("Message from logger2")
        
#         log_content = log_file.read_text()
#         assert "Message from logger1" in log_content
#         assert "Message from logger2" in log_content
    
#     def test_logger_level_propagation(self):
#         """Test that log level changes propagate correctly."""
#         logger = setup_logger("propagation_test", level="INFO")
        
#         # Should not log DEBUG messages initially
#         with patch.object(logger, 'debug') as mock_debug:
#             logger.debug("Debug message")
#             mock_debug.assert_called_once()
        
#         # Change level to DEBUG
#         logger.setLevel(logging.DEBUG)
#         for handler in logger.handlers:
#             handler.setLevel(logging.DEBUG)
        
#         # Should now log DEBUG messages
#         with patch.object(logger, 'debug') as mock_debug:
#             logger.debug("Debug message")
#             mock_debug.assert_called_once()
    
#     @pytest.mark.slow
#     def test_log_rotation(self, tmp_path):
#         """Test log file rotation functionality."""
#         log_file = tmp_path / "rotation_test.log"
        
#         # Create logger with small max_bytes for testing
#         logger = setup_logger(
#             "rotation_test",
#             log_file=str(log_file),
#             max_bytes=100,  # Very small for testing
#             backup_count=2
#         )
        
#         # Write enough messages to trigger rotation
#         for i in range(50):
#             logger.info(f"Test message {i} - this is a longer message to fill up the log file")
        
#         # Check that rotation occurred
#         assert log_file.exists()
#         # Note: Actual rotation testing would require more complex file size checking


# @pytest.mark.integration
# class TestLoggerEnvironmentIntegration:
#     """Integration tests with environment variables."""
    
#     def test_logger_with_env_variables(self):
#         """Test logger setup with environment variable configuration."""
#         with patch.dict(os.environ, {'ESMD_LOG_LEVEL': 'DEBUG'}):
#             logger = setup_logger("env_test")
            
#             assert logger.level == logging.DEBUG
    
#     def test_logger_file_from_env(self, tmp_path):
#         """Test logger file configuration from environment."""
#         log_file = tmp_path / "env_test.log"
        
#         with patch.dict(os.environ, {'ESMD_LOG_FILE': str(log_file)}):
#             # This would require modifying setup_logger to check env vars
#             # For now, just test that the pattern works
#             logger = setup_logger("env_file_test", log_file=os.getenv('ESMD_LOG_FILE'))
            
#             logger.info("Environment log test")
#             assert log_file.exists()
#             assert "Environment log test" in log_file.read_text() 