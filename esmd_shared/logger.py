"""
Enhanced Logging Utility for EsmdFHIRClient.

This module provides a robust logging setup with configurable levels,
formatters, handlers, validation, and error handling.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional, Dict, Any, List, Union, TextIO
from pathlib import Path
from datetime import datetime
import threading

from .models import LoggerConfig, ValidationResult
from .exceptions import ValidationError, FileOperationError, ConfigurationError
from .utils import validate_file_path, sanitize_filename


class EnhancedLogger:
    def __getattr__(self, name):
        # Forward attribute access to the underlying logger
        return getattr(self._logger, name)
    """
    Enhanced logger wrapper with additional features.
    
    Features:
    - Performance monitoring
    - Context management
    - Structured logging
    - Safe error handling
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize enhanced logger wrapper.
        
        Args:
            logger: Base logger instance
        """
        self._logger = logger
        self._context: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def set_context(self, **kwargs: Any) -> None:
        """Set logging context for all subsequent log messages."""
        with self._lock:
            self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear logging context."""
        with self._lock:
            self._context.clear()
    
    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format message with context."""
        parts = [message]
        
        # Add context
        if self._context:
            context_str = " | ".join(f"{k}={v}" for k, v in self._context.items())
            parts.append(f"[{context_str}]")
        
        # Add extra data
        if extra:
            extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
            parts.append(f"({extra_str})")
        
        return " ".join(parts)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self._logger.debug(self._format_message(message, kwargs))
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self._logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self._logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self._logger.error(self._format_message(message, kwargs))
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with context."""
        self._logger.critical(self._format_message(message, kwargs))
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with context."""
        self._logger.exception(self._format_message(message, kwargs))
    
    @property
    def level(self) -> int:
        """Get logger level."""
        return self._logger.level
    
    @level.setter
    def level(self, level: Union[int, str]) -> None:
        """Set logger level."""
        if isinstance(level, str):
            level = get_log_level(level)
        self._logger.setLevel(level)


def setup_logger(
    name: str,
  
    config: Optional[LoggerConfig] = None,
    enhanced: bool = True
) -> Union[logging.Logger, EnhancedLogger]:
    """
    Set up a logger with comprehensive configuration and validation.
    
    Args:
        name: Logger name (typically __name__ or class name)
        level: Logging level (e.g., 'DEBUG', 'INFO')
        config: LoggerConfig instance with all settings
        enhanced: Whether to return EnhancedLogger wrapper
        
    Returns:
        Union[logging.Logger, EnhancedLogger]: Configured logger instance
        
    Raises:
        ValidationError: If configuration is invalid
        FileOperationError: If log file cannot be created
        ConfigurationError: If logger setup fails
    """
    # Validate inputs
    if not name or not name.strip():
        raise ValidationError("Logger name cannot be empty", field="name", value=name)
    
    # Use default config if none provided
    if config is None:
        config = LoggerConfig(
            name=name,
            level=os.getenv('ESMD_LOG_LEVEL', 'INFO'),
            file_path=os.getenv('ESMD_LOG_FILE'),
            console_logging=True
        )
    
    # Validate configuration
    validation = validate_logger_config(config)
    if not validation.is_valid:
        raise ValidationError(
            f"Invalid logger configuration: {', '.join(validation.errors)}",
            field="config",
            value=config
        )
    
    try:
        logger = logging.getLogger(name)
        
        # Clear existing handlers to avoid duplicates
        if logger.handlers:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        # Set logging level
        log_level = get_log_level(config.level)
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = create_formatter(config.format_string)
        
        # Add console handler if requested
        if config.console_logging:
            console_handler = create_console_handler(log_level, formatter)
            logger.addHandler(console_handler)
            logger.info("Console logging enabled")
        
        # Add file handler if file path specified
        if config.file_path:
            file_handler = create_file_handler(
                config.file_path,
                log_level,
                formatter,
                config.max_bytes,
                config.backup_count
            )
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {config.file_path}")
        
        # Prevent propagation to root logger
        logger.propagate = True

        if enhanced:
            return EnhancedLogger(logger)
        else:
            return logger
            
    except Exception as e:
        raise ConfigurationError(f"Failed to setup logger '{name}': {e}") from e


def validate_logger_config(config: LoggerConfig) -> ValidationResult:
    """
    Validate logger configuration.
    
    Args:
        config: LoggerConfig to validate
        
    Returns:
        ValidationResult: Validation results
    """
    result = ValidationResult(is_valid=True)
    
    # Validate name
    if not config.name or not config.name.strip():
        result.errors.append("Logger name cannot be empty")
    
    # Validate level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if config.level.upper() not in valid_levels:
        result.errors.append(f"Invalid log level: {config.level}")
    
    # Validate file path if provided
    if config.file_path:
        path_validation = validate_file_path(config.file_path)
        if not path_validation.is_valid:
            result.errors.extend(path_validation.errors)
    
    # Validate max_bytes
    if config.max_bytes <= 0:
        result.errors.append("max_bytes must be positive")
    elif config.max_bytes < 1024:  # Less than 1KB
        result.warnings.append("max_bytes is very small, may cause frequent rotation")
    
    # Validate backup_count
    if config.backup_count < 0:
        result.errors.append("backup_count cannot be negative")
    elif config.backup_count > 100:
        result.warnings.append("backup_count is very high, may consume excessive disk space")
    
    result.is_valid = len(result.errors) == 0
    return result


def get_log_level(level: Optional[str]) -> int:
    """
    Convert string log level to logging constant with validation.
    
    Args:
        level: String log level (case-insensitive)
        
    Returns:
        int: Logging level constant
        
    Raises:
        ValidationError: If level is invalid
    """
    if not level:
        # Try to get from environment
        level = os.getenv('ESMD_LOG_LEVEL', 'INFO')
    
    if not isinstance(level, str):
        raise ValidationError(
            f"Log level must be a string, got {type(level).__name__}",
            field="level",
            value=level
        )
    
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.CRITICAL
    }
    
    level_upper = level.upper().strip()
    if level_upper not in level_map:
        valid_levels = list(set(level_map.keys()))
        raise ValidationError(
            f"Invalid log level '{level}'. Valid levels: {valid_levels}",
            field="level",
            value=level
        )
    
    return level_map[level_upper]


def create_formatter(format_string: Optional[str] = None) -> logging.Formatter:
    """
    Create a log formatter with validation.
    
    Args:
        format_string: Custom format string. If None, uses default.
        
    Returns:
        logging.Formatter: Configured formatter
        
    Raises:
        ValidationError: If format string is invalid
    """
    if format_string and not isinstance(format_string, str):
        raise ValidationError(
            f"Format string must be a string, got {type(format_string).__name__}",
            field="format_string",
            value=format_string
        )
    
    if not format_string:
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
    
    try:
        return logging.Formatter(
            format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Invalid format string: {e}",
            field="format_string",
            value=format_string
        )


def create_console_handler(
    level: int, 
    formatter: logging.Formatter,
    stream: Optional[TextIO] = None
) -> logging.StreamHandler:
    """
    Create console handler with validation.
    
    Args:
        level: Log level
        formatter: Log formatter
        stream: Output stream (default: sys.stdout)
        
    Returns:
        logging.StreamHandler: Configured console handler
    """
    if stream is None:
        stream = sys.stdout
    
    handler = logging.StreamHandler(stream)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def create_file_handler(
    file_path: str,
    level: int,
    formatter: logging.Formatter,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.handlers.RotatingFileHandler:
    """
    Create rotating file handler with comprehensive validation.
    
    Args:
        file_path: Path to log file
        level: Log level
        formatter: Log formatter
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        logging.handlers.RotatingFileHandler: Configured file handler
        
    Raises:
        ValidationError: If parameters are invalid
        FileOperationError: If file cannot be created
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValidationError("File path cannot be empty", field="file_path", value=file_path)
    
    if max_bytes <= 0:
        raise ValidationError("max_bytes must be positive", field="max_bytes", value=max_bytes)
    
    if backup_count < 0:
        raise ValidationError("backup_count cannot be negative", field="backup_count", value=backup_count)
    
    # Validate and sanitize file path
    path_validation = validate_file_path(file_path)
    if not path_validation.is_valid:
        raise ValidationError(
            f"Invalid file path: {', '.join(path_validation.errors)}",
            field="file_path",
            value=file_path
        )
    
    try:
        # Ensure log directory exists
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        
        return handler
        
    except PermissionError:
        raise FileOperationError(
            f"Permission denied creating log file: {file_path}",
            file_path=file_path,
            operation="create"
        )
    except OSError as e:
        raise FileOperationError(
            f"OS error creating log file {file_path}: {e}",
            file_path=file_path,
            operation="create"
        )
    except Exception as e:
        raise FileOperationError(
            f"Unexpected error creating log file {file_path}: {e}",
            file_path=file_path,
            operation="create"
        )


def configure_root_logger(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    disable_existing: bool = True,
    format_string: Optional[str] = None
) -> None:
    """
    Configure the root logger for the entire application with validation.
    
    Args:
        level: Root logging level
        log_file: Optional log file for root logger
        disable_existing: If True, disables existing loggers
        format_string: Custom format string
        
    Raises:
        ValidationError: If configuration is invalid
        FileOperationError: If log file cannot be created
    """
    # Validate level
    log_level = get_log_level(level)
    
    if disable_existing:
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = create_formatter(format_string)
    
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True  # Override existing configuration
    )
    
    # Add file handler if specified
    if log_file:
        root_logger = logging.getLogger()
        file_handler = create_file_handler(log_file, log_level, formatter)
        root_logger.addHandler(file_handler)


def get_logger_info() -> Dict[str, Any]:
    """
    Get comprehensive information about current logging configuration.
    
    Returns:
        Dict[str, Any]: Detailed logging configuration information
    """
    root_logger = logging.getLogger()
    
    info = {
        'root_level': logging.getLevelName(root_logger.level),
        'effective_level': logging.getLevelName(root_logger.getEffectiveLevel()),
        'handlers': [],
        'loggers': [],
        'total_loggers': len(logging.getLogger().manager.loggerDict),
        'timestamp': datetime.now().isoformat()
    }
    
    # Get handler information
    for handler in root_logger.handlers:
        handler_info = {
            'type': handler.__class__.__name__,
            'level': logging.getLevelName(handler.level),
            'formatter': handler.formatter.__class__.__name__ if handler.formatter else None
        }
        
        if isinstance(handler, logging.FileHandler):
            handler_info.update({
                'file': handler.baseFilename,
                'mode': getattr(handler, 'mode', 'unknown')
            })
            
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler_info.update({
                    'max_bytes': handler.maxBytes,
                    'backup_count': handler.backupCount
                })
        
        if isinstance(handler, logging.StreamHandler):
            stream_name = getattr(handler.stream, 'name', str(handler.stream))
            handler_info['stream'] = stream_name
            
        info['handlers'].append(handler_info)
    
    # Get active loggers (limited to first 50 for performance)
    logger_names = list(logging.getLogger().manager.loggerDict.keys())[:50]
    for name in logger_names:
        logger = logging.getLogger(name)
        if logger.handlers or logger.level != logging.NOTSET or not logger.propagate:
            logger_info = {
                'name': name,
                'level': logging.getLevelName(logger.level),
                'effective_level': logging.getLevelName(logger.getEffectiveLevel()),
                'handlers': len(logger.handlers),
                'propagate': logger.propagate,
                'disabled': logger.disabled
            }
            info['loggers'].append(logger_info)
    
    return info


def cleanup_loggers() -> int:
    """
    Clean up and close all logger handlers.
    
    Returns:
        int: Number of handlers closed
    """
    handlers_closed = 0
    
    # Close root logger handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        try:
            handler.close()
            root_logger.removeHandler(handler)
            handlers_closed += 1
        except Exception:
            pass  # Ignore errors during cleanup
    
    # Close handlers for all loggers
    for name in list(logging.getLogger().manager.loggerDict.keys()):
        try:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                    handlers_closed += 1
                except Exception:
                    pass  # Ignore errors during cleanup
        except Exception:
            pass  # Ignore errors during cleanup
    
    return handlers_closed


def set_logger_level(name: str, level: Union[str, int]) -> None:
    """
    Set logger level with validation.
    
    Args:
        name: Logger name
        level: New log level
        
    Raises:
        ValidationError: If level is invalid
    """
    if isinstance(level, str):
        level = get_log_level(level)
    elif not isinstance(level, int):
        raise ValidationError(
            f"Level must be string or int, got {type(level).__name__}",
            field="level",
            value=level
        )
    
    logger = logging.getLogger(name)
    logger.setLevel(level)


def get_logger_names() -> List[str]:
    """
    Get list of all active logger names.
    
    Returns:
        List[str]: List of logger names
    """
    names = ['root']  # Include root logger
    names.extend(logging.getLogger().manager.loggerDict.keys())
    return sorted(names) 