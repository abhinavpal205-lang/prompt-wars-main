"""FastAPI dependencies: db session, settings, gateway, sender, rate limiter."""

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.security import NoteCipher
from app.services.notifier import EmailSender
from app.services.openai_client import AIGateway

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


def get_gateway(request: Request) -> AIGateway:
    """The AI gateway bound to this app (a fake in tests)."""
    return cast(AIGateway, request.app.state.gateway)


def get_email_sender(request: Request) -> EmailSender:
    """The notification sender bound to this app (console stub by default)."""
    return cast(EmailSender, request.app.state.email_sender)


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
CipherDep = Annotated[NoteCipher, Depends(get_cipher)]
GatewayDep = Annotated[AIGateway, Depends(get_gateway)]
SenderDep = Annotated[EmailSender, Depends(get_email_sender)]
