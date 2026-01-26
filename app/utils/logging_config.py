"""
Logging configuration for the application.
Provides detailed logging with automatic log rotation to manage file sizes.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Create logs directory if it doesn't exist
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file configuration
LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "error.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Keep 5 backup files (total ~50MB max for app.log)

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level=logging.INFO):
    """
    Set up application-wide logging with rotation.

    Args:
        log_level: Logging level (default: logging.INFO)

    Returns:
        logging.Logger: Configured root logger
    """
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler - show INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler for all logs
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Separate rotating file handler for errors only
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)  # Only errors and critical
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Log the initialization
    root_logger.info("=" * 80)
    root_logger.info(f"Logging system initialized at {datetime.now()}")
    root_logger.info(f"Log directory: {LOGS_DIR}")
    root_logger.info(f"Main log file: {LOG_FILE}")
    root_logger.info(f"Error log file: {ERROR_LOG_FILE}")
    root_logger.info(f"Max log size: {MAX_LOG_SIZE / (1024*1024):.1f} MB")
    root_logger.info(f"Backup count: {BACKUP_COUNT}")
    root_logger.info("=" * 80)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


# Utility function to log exceptions with full traceback
def log_exception(logger: logging.Logger, message: str, exc: Exception = None):
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        message: Custom message
        exc: Exception object (optional, will be auto-captured if in except block)
    """
    logger.exception(f"{message}: {str(exc) if exc else ''}")
