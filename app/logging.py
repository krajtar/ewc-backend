"""Structured logging configuration using structlog.

Provides:
- JSON-structured log output via structlog.
- A Starlette middleware that attaches a ``request_id`` to every log
  record and returns it in the ``X-Request-ID`` response header.
"""

import uuid
from typing import Any, Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog processors and stdlib bridge."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to *name*."""
    return structlog.get_logger(name)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID into logs and response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        logger = get_logger("request")
        logger.info("request_started")

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        logger.info("request_finished", status_code=response.status_code)

        return response
