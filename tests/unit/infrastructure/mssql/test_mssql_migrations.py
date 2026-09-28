"""Unit tests for MSSQL Alembic migrations."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_migrations_upgrade_and_downgrade() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection

        # Run all migrations up to head
        command.upgrade(config, "head")

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        assert "conversations" in tables
        assert "messages" in tables
        assert "outbox_messages" in tables
        assert "idempotency_keys" in tables
        assert "audit_logs" in tables
        assert "stream_buffer_chunks" in tables

        # Downgrade to initial revision
        command.downgrade(config, "d60987c4b536")
        inspector_after = inspect(connection)
        tables_after = set(inspector_after.get_table_names())
        assert "idempotency_keys" not in tables_after
        assert "audit_logs" not in tables_after
        assert "stream_buffer_chunks" not in tables_after
