"""FastAPI dependencies: db session, settings, cipher, and the rate limiter."""

from collections.abc import Iterator
from typing import cast

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.security import NoteCipher

# Global limiter; per-route limits are declared on the route handlers.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def get_settings_dep(request: Request) -> Settings:
    """The settings instance bound to this app (overridable in tests)."""
    return cast(Settings, request.app.state.settings)


def get_session(request: Request) -> Iterator[Session]:
    """Yield a database session bound to this app's engine."""
    engine = cast(Engine, request.app.state.engine)
    with Session(engine) as session:
        yield session


def get_cipher(request: Request) -> NoteCipher:
    """The note cipher bound to this app."""
    return cast(NoteCipher, request.app.state.cipher)
