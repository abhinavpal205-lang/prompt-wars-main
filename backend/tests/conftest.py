"""Shared fixtures: in-memory database and fake AI gateway."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session

from app.db import create_db_engine, init_db
from tests.fakes import FakeGateway


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
