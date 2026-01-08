"""Logging configuration for the application."""

import logging
import sys
from typing import Optional
from .config import get_settings


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    settings = get_settings()

    logger = logging.getLogger(name or __name__)

    # Only configure if not already configured
    if not logger.handlers:
        # Set level from config
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Formatter
        if settings.ENABLE_DEBUG_LOGGING:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger


def log_function_call(logger: logging.Logger, function_name: str, **kwargs):
    """
    Log a function call with parameters.

    Args:
        logger: Logger instance
        function_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Calling {function_name}({params_str})")


def log_function_result(logger: logging.Logger, function_name: str, success: bool, message: str = ""):
    """
    Log function execution result.

    Args:
        logger: Logger instance
        function_name: Name of the function
        success: Whether execution was successful
        message: Optional message
    """
    status = "SUCCESS" if success else "FAILURE"
    log_msg = f"{function_name} - {status}"
    if message:
        log_msg += f": {message}"

    if success:
        logger.info(log_msg)
    else:
        logger.error(log_msg)
