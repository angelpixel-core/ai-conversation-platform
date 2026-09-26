"""MSSQL Engine and session factory configuration for SQLModel."""

from collections.abc import Callable
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


def create_mssql_engine(
    url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> Engine:
    """Create a SQLAlchemy / SQLModel Engine with connection pooling.

    Args:
        url: Database connection string (e.g. mssql+pymssql://... or sqlite:///:memory:).
        pool_size: The number of connections to keep open inside the connection pool.
        max_overflow: The number of connections to allow in overflow.
        pool_timeout: Seconds to wait before giving up on getting a connection from pool.
        pool_recycle: Seconds after which a connection is recycled.
        pool_pre_ping: If True, tests connection health before checkout.
        echo: If True, logs SQL statements to stdout.

    Returns:
        Engine: Configured SQLAlchemy Engine.
    """
    engine_kwargs: dict[str, Any] = {"echo": echo}

    if url.startswith("sqlite"):
        # SQLite in-memory or file databases do not use standard QueuePool arguments
        return create_engine(url, **engine_kwargs)

    engine_kwargs.update(
        {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": pool_pre_ping,
        }
    )
    return create_engine(url, **engine_kwargs)


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """Create a callable factory that returns a new SQLModel Session bound to the engine.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Callable[[], Session]: Factory returning open sessions.
    """
    return lambda: Session(engine)
