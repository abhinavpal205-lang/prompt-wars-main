"""Application factory.

Run with: ``uvicorn app.main:create_app --factory``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import Settings, get_settings
from app.db import create_db_engine, init_db
from app.deps import limiter
from app.errors import register_exception_handlers
from app.logging_config import setup_logging
from app.security import NoteCipher


def _handle_rate_limit(request: Request, exc: Exception) -> Response:
    """Typed adapter around slowapi's rate-limit response."""
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app with all middleware, routes, and handlers."""
    setup_logging()
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        init_db(application.state.engine)
        yield

    app = FastAPI(title="Sahaay API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = create_db_engine(settings.database_url)
    app.state.cipher = NoteCipher(settings.fernet_key)

    # Same-origin in production (nginx proxies /api); CORS covers local dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
    register_exception_handlers(app)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe for Docker and compose health checks."""
        return {"status": "ok"}

    return app
