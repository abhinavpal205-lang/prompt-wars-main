"""Custom exceptions and clean JSON error handling.

Errors never leak tracebacks, secrets, or user content to clients.
"""

import logging
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected application errors."""

    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "internal_error"

    def __init__(self, message: str = "Something went wrong.") -> None:
        super().__init__(message)
        self.message = message


class RealtimeUnavailableError(AppError):
    """Voice mode requested but OpenAI is not configured or unreachable."""

    status_code = 503
    code = "realtime_unavailable"


class UpstreamServiceError(AppError):
    """An upstream AI call failed in a way we could not degrade around."""

    status_code = 502
    code = "upstream_error"


class CalmingContextError(AppError):
    """A calming token was requested without valid non-crisis context."""

    status_code = 400
    code = "calming_context_required"


def _app_error_response(error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers mapping exceptions to clean JSON bodies."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError %s: %s", exc.code, exc.message)
        return _app_error_response(exc)

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        # Log the class only — never the payload, which may contain
        # sensitive check-in content.
        logger.error("Unhandled %s", type(exc).__name__, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Something went wrong."}},
        )
