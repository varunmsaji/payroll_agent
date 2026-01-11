"""
Centralized Logging Configuration for HRMS Payroll Backend

Features:
- Rotating file handlers (5MB max, 5 backups)
- Structured JSON logging for production
- Human-readable console logging for development
- Separate error log file
- Per-module log files
- Request context tracking with unique request IDs
"""

import logging
import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from contextvars import ContextVar
import uuid

# ============================================================
# CONFIGURATION
# ============================================================

# Base directory for logs (relative to project root)
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log levels
DEFAULT_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.DEBUG

# File rotation settings
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5

# Request context for tracking request IDs across logs
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# ============================================================
# CUSTOM FORMATTERS
# ============================================================

class DetailedFormatter(logging.Formatter):
    """Human-readable detailed formatter for console and file output."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            record.request_id = f"[{request_id[:8]}]"
        else:
            record.request_id = ""
        
        # Add exception info if present
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "request_id": request_id_var.get() or None,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


# ============================================================
# LOGGER FACTORY
# ============================================================

# Cache for created loggers to avoid duplicate handlers
_logger_cache: Dict[str, logging.Logger] = {}

# Human-readable format
DETAILED_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d "
    "%(request_id)s | %(message)s"
)

# Date format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    enable_json: bool = True,
    enable_console: bool = True
) -> logging.Logger:
    """
    Get a configured logger with console and file handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional specific log file name (e.g., "attendance.log")
        enable_json: Enable JSON log file for structured logging
        enable_console: Enable console output
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__, "attendance.log")
        logger.info("Processing attendance for employee", extra={"extra_data": {"employee_id": 123}})
    """
    # Return cached logger if already exists
    cache_key = f"{name}_{log_file}"
    if cache_key in _logger_cache:
        return _logger_cache[cache_key]
    
    logger = logging.getLogger(name)
    
    # Only configure if this logger doesn't have handlers yet
    if logger.handlers:
        return logger
    
    logger.setLevel(DEFAULT_LOG_LEVEL)
    logger.propagate = False  # Prevent duplicate logs from parent loggers
    
    # --------------------------------------------------------
    # Console Handler (human-readable)
    # --------------------------------------------------------
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(CONSOLE_LOG_LEVEL)
        console_formatter = DetailedFormatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # --------------------------------------------------------
    # Main File Handler (human-readable, rotating)
    # --------------------------------------------------------
    if log_file:
        file_name = log_file
    else:
        # Derive file name from module name
        module_name = name.split(".")[-1]
        file_name = f"{module_name}.log"
    
    file_handler = RotatingFileHandler(
        LOG_DIR / file_name,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(FILE_LOG_LEVEL)
    file_formatter = DetailedFormatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # --------------------------------------------------------
    # JSON File Handler (structured, for production parsing)
    # --------------------------------------------------------
    if enable_json:
        json_file_name = file_name.replace(".log", ".json.log")
        json_handler = RotatingFileHandler(
            LOG_DIR / json_file_name,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        json_handler.setLevel(FILE_LOG_LEVEL)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
    
    # --------------------------------------------------------
    # Error File Handler (errors only, all modules)
    # --------------------------------------------------------
    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = DetailedFormatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)
    
    # Cache the logger
    _logger_cache[cache_key] = logger
    
    return logger


# ============================================================
# REQUEST ID MANAGEMENT
# ============================================================

def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set or generate a request ID for the current context.
    
    Args:
        request_id: Optional existing request ID. If None, generates a new UUID.
    
    Returns:
        The request ID that was set.
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Get the current request ID."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear the current request ID."""
    request_id_var.set("")


# ============================================================
# LOGGING HELPERS
# ============================================================

def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any
) -> None:
    """
    Log a message with additional context data.
    
    Args:
        logger: Logger instance
        level: Logging level (e.g., logging.INFO)
        message: Log message
        **context: Additional context to include in structured logs
    
    Example:
        log_with_context(logger, logging.INFO, "User logged in", user_id=123, ip="1.2.3.4")
    """
    extra = {"extra_data": context} if context else {}
    logger.log(level, message, extra=extra)


def log_function_entry(
    logger: logging.Logger,
    func_name: str,
    **params: Any
) -> None:
    """Log function entry with parameters."""
    sanitized_params = _sanitize_params(params)
    logger.debug(f"ENTER: {func_name}", extra={"extra_data": {"params": sanitized_params}})


def log_function_exit(
    logger: logging.Logger,
    func_name: str,
    result: Any = None,
    duration_ms: Optional[float] = None
) -> None:
    """Log function exit with optional result and duration."""
    data = {}
    if duration_ms is not None:
        data["duration_ms"] = round(duration_ms, 2)
    if result is not None:
        data["result_type"] = type(result).__name__
    logger.debug(f"EXIT: {func_name}", extra={"extra_data": data})


def log_error(
    logger: logging.Logger,
    message: str,
    exception: Optional[Exception] = None,
    **context: Any
) -> None:
    """
    Log an error with full context and exception details.
    
    Args:
        logger: Logger instance
        message: Error message
        exception: Optional exception object
        **context: Additional context
    """
    extra = {"extra_data": context} if context else {}
    if exception:
        logger.error(message, exc_info=exception, extra=extra)
    else:
        logger.error(message, extra=extra)


def log_db_query(
    logger: logging.Logger,
    query_type: str,
    table: str,
    params: Optional[Dict] = None,
    row_count: Optional[int] = None,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log database query with details.
    
    Args:
        logger: Logger instance
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        params: Query parameters (will be sanitized)
        row_count: Number of rows affected/returned
        duration_ms: Query duration in milliseconds
    """
    data = {
        "query_type": query_type,
        "table": table,
    }
    if params:
        data["params"] = _sanitize_params(params)
    if row_count is not None:
        data["row_count"] = row_count
    if duration_ms is not None:
        data["duration_ms"] = round(duration_ms, 2)
    
    logger.debug(f"DB {query_type}: {table}", extra={"extra_data": data})


# ============================================================
# SANITIZATION
# ============================================================

SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "apikey", 
    "authorization", "auth", "credential", "ssn", "credit_card"
}


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive parameters for logging.
    
    Masks values for keys that appear to be sensitive.
    """
    if not params:
        return {}
    
    sanitized = {}
    for key, value in params.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_params(value)
        else:
            sanitized[key] = value
    
    return sanitized


# ============================================================
# MODULE LOGGERS (Pre-configured for convenience)
# ============================================================

def get_api_logger(module_name: str = "api") -> logging.Logger:
    """Get logger for API layer."""
    return get_logger(f"hrms.api.{module_name}", "api_requests.log")


def get_db_logger(module_name: str = "database") -> logging.Logger:
    """Get logger for database layer."""
    return get_logger(f"hrms.db.{module_name}", "database.log")


def get_service_logger(module_name: str = "service") -> logging.Logger:
    """Get logger for service layer."""
    return get_logger(f"hrms.service.{module_name}", "services.log")


def get_attendance_logger() -> logging.Logger:
    """Get logger for attendance operations."""
    return get_logger("hrms.attendance", "attendance.log")


def get_payroll_logger() -> logging.Logger:
    """Get logger for payroll operations."""
    return get_logger("hrms.payroll", "payroll.log")


def get_leave_logger() -> logging.Logger:
    """Get logger for leave management."""
    return get_logger("hrms.leave", "leave.log")
