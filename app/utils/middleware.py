"""
Request/Response Logging Middleware for FastAPI

Features:
- Logs all incoming requests with method, path, headers, client IP
- Logs response status codes and timing
- Generates unique request IDs for tracing
- Masks sensitive data in request bodies
- Supports structured JSON logging
"""

import json
import time
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import (
    SENSITIVE_KEYS,
    clear_request_id,
    get_api_logger,
    get_request_id,
    set_request_id,
)

# Initialize API logger
logger = get_api_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs:
    - Request method, path, query params
    - Client IP address
    - Request headers (sanitized)
    - Request body for POST/PUT/PATCH (sanitized)
    - Response status code
    - Request duration
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = set_request_id()

        # Start timing
        start_time = time.perf_counter()

        # Extract request details
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # Log incoming request
        log_data = {
            "event": "request_start",
            "request_id": request_id,
            "method": method,
            "path": path,
            "query_params": query_params if query_params else None,
            "client_ip": client_ip,
        }

        # Add sanitized headers
        headers = self._sanitize_headers(dict(request.headers))
        if headers:
            log_data["headers"] = headers

        logger.info(f"→ {method} {path}", extra={"extra_data": log_data})

        # Log request body for write operations
        if method in ("POST", "PUT", "PATCH"):
            await self._log_request_body(request)

        # Process request
        response: Optional[Response] = None
        error: Optional[Exception] = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                f"✗ {method} {path} - Exception",
                exc_info=e,
                extra={
                    "extra_data": {
                        "event": "request_error",
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "duration_ms": round(duration_ms, 2),
                        "error": str(e),
                    }
                },
            )
            # Re-raise to let FastAPI handle it
            raise
        finally:
            clear_request_id()

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        status_code = response.status_code
        log_level = self._get_log_level_for_status(status_code)

        status_symbol = "✓" if status_code < 400 else "✗"

        response_log_data = {
            "event": "request_complete",
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        logger.log(
            log_level,
            f"{status_symbol} {method} {path} → {status_code} ({duration_ms:.2f}ms)",
            extra={"extra_data": response_log_data},
        )

        # Add request ID to response headers for client tracing
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, checking forwarded headers."""
        # Check for proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove or mask sensitive headers."""
        sanitized = {}
        skip_headers = {"cookie", "set-cookie"}

        for key, value in headers.items():
            key_lower = key.lower()

            if key_lower in skip_headers:
                continue

            if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    async def _log_request_body(self, request: Request) -> None:
        """Log sanitized request body for write operations."""
        try:
            # Read body
            body = await request.body()
            if not body:
                return

            # Try to parse as JSON
            try:
                body_json = json.loads(body)
                sanitized_body = self._sanitize_body(body_json)
                logger.debug("Request body", extra={"extra_data": {"body": sanitized_body}})
            except json.JSONDecodeError:
                # Not JSON, log size only
                logger.debug(f"Request body (non-JSON, {len(body)} bytes)")
        except Exception as e:
            logger.debug(f"Could not log request body: {e}")

    def _sanitize_body(self, body: Any) -> Any:
        """Recursively sanitize sensitive fields in request body."""
        if isinstance(body, dict):
            sanitized = {}
            for key, value in body.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_body(value)
            return sanitized
        elif isinstance(body, list):
            return [self._sanitize_body(item) for item in body]
        else:
            return body

    def _get_log_level_for_status(self, status_code: int) -> int:
        """Get appropriate log level based on status code."""
        import logging

        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        else:
            return logging.INFO


def add_logging_middleware(app: FastAPI) -> None:
    """
    Add request logging middleware to FastAPI app.

    Usage:
        from app.utils.middleware import add_logging_middleware

        app = FastAPI()
        add_logging_middleware(app)
    """
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware initialized")
