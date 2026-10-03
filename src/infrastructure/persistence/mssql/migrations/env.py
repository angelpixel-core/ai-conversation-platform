"""Alembic environment configuration for SQLModel migrations on MSSQL."""

import logging
import os
import re
from logging.config import fileConfig
from urllib.parse import urlsplit, urlunsplit

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import (
    Column,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    create_engine,
    engine_from_config,
    pool,
    text,
)
from sqlmodel import SQLModel

# Ensure all SQLModel physical models are registered in metadata
import src.infrastructure.persistence.mssql.models  # noqa: F401

logger = logging.getLogger("alembic.env")


# SQL Server requires version_num column length > 32 for descriptive revision names
def _custom_version_table_impl(
    self,
    *,
    version_table: str,
    version_table_schema: str | None,
    version_table_pk: bool,
    **kw,
) -> Table:
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(128), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc"))
    return vt


DefaultImpl.version_table_impl = _custom_version_table_impl

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# Allow DATABASE_URL environment variable to override config
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_column_length=128,
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_database_exists(url_str: str | None) -> None:
    """Ensure target database exists in SQL Server before running migrations."""
    if not url_str:
        return
    try:
        parsed = urlsplit(url_str)
        if not parsed.path or parsed.path == "/master":
            return
        db_name = parsed.path.lstrip("/")
        if not re.match(r"^[A-Za-z0-9_]+$", db_name):
            return

        master_url = urlunsplit(
            (parsed.scheme, parsed.netloc, "/master", parsed.query, parsed.fragment)
        )
        engine = create_engine(master_url)
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            query = text(
                f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db_name}') "  # noqa: S608 # nosec B608
                f"CREATE DATABASE [{db_name}];"
            )
            conn.execute(query)
        engine.dispose()
    except Exception as exc:
        logger.warning("Could not verify database existence: %s", exc)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    target_url = config.get_main_option("sqlalchemy.url")
    _ensure_database_exists(target_url)

    connectable = config.attributes.get("connection", None)

    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_column_length=128,
            )

            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            version_table_column_length=128,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
