import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from commerceos.platform.database.models import Base

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def _engine_kwargs(database_url: str) -> dict:
    """Return extra kwargs for create_engine based on the database dialect."""
    kwargs = {"future": True}
    if database_url.startswith("postgresql"):
        # Render PostgreSQL requires SSL; allow env override for flexibility.
        sslmode = os.environ.get("PGSSLMODE", "require")
        kwargs["connect_args"] = {"sslmode": sslmode}
    return kwargs


def get_engine(database_url: str, echo: bool = False) -> Engine:
    """Create or return the global SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url, echo=echo, **_engine_kwargs(database_url)
        )
    return _engine


def get_session_factory(database_url: str, echo: bool = False) -> sessionmaker:
    """Create or return the global session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine(database_url, echo)
        _SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionFactory


def get_session(database_url: str, echo: bool = False) -> Session:
    """Return a new database session."""
    factory = get_session_factory(database_url, echo)
    return factory()


def create_all(database_url: str, echo: bool = False) -> None:
    """Create all tables. Useful for testing and bootstrapping."""
    engine = get_engine(database_url, echo)
    Base.metadata.create_all(bind=engine)


def reset_engine() -> None:
    """Reset the global engine. Useful in tests."""
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None
