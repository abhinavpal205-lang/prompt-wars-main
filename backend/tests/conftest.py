"""Shared fixtures: in-memory database, fake AI gateway, and a test app."""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.config import Settings
from app.db import create_db_engine, init_db
from app.deps import limiter
from app.main import create_app
from tests.fakes import FakeGateway, RecordingEmailSender


@pytest.fixture
def session() -> Iterator[Session]:
    """A session on a fresh in-memory SQLite database."""
    engine = create_db_engine("sqlite://")
    init_db(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def gateway() -> FakeGateway:
    """A configured fake gateway with no outputs seeded yet."""
    return FakeGateway()


@pytest.fixture
def offline_gateway() -> FakeGateway:
    """A gateway in offline stub mode (no API key)."""
    return FakeGateway(configured=False)


@pytest.fixture
def sent_emails() -> RecordingEmailSender:
    """Captures every parent notification the app tries to deliver."""
    return RecordingEmailSender()


@pytest.fixture
def app(gateway: FakeGateway, sent_emails: RecordingEmailSender) -> FastAPI:
    """A full app on an in-memory database with fake external services."""
    settings = Settings(
        database_url="sqlite://",
        openai_api_key="",
        smtp_host="",
        smtp_from="",
        fernet_key="",
    )
    application = create_app(settings)
    application.state.gateway = gateway
    application.state.email_sender = sent_emails
    init_db(application.state.engine)  # httpx's ASGI transport skips lifespan
    limiter.enabled = False  # individual tests opt back in
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """An async HTTP client against the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
