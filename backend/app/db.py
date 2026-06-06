"""Database engine creation and initialization."""

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app import models as _models  # noqa: F401  (register tables with metadata)


def create_db_engine(database_url: str) -> Engine:
    """Create an engine, handling SQLite quirks for app and tests alike."""
    if database_url.startswith("sqlite"):
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            # In-memory DB (tests): share one connection across sessions.
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        db_path = Path(database_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def init_db(engine: Engine) -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)
