"""Unit tests for infrastructure settings and configuration."""

from src.infrastructure.shared.config.settings import (
    DatabaseSettings,
    MessagingDriver,
    MessagingSettings,
    PersistenceDriver,
    Settings,
    get_settings,
)


def test_default_persistence_driver_is_in_memory() -> None:
    settings = Settings()
    assert settings.PERSISTENCE_DRIVER == PersistenceDriver.IN_MEMORY


def test_database_settings_url_construction() -> None:
    db_settings = DatabaseSettings(
        DB_SERVER="db.example.com",
        DB_PORT=1433,
        DB_NAME="TestDB",
        DB_USER="usr",
        DB_PASSWORD="p@ssword#123",  # noqa: S106
    )
    url = db_settings.get_database_url()
    assert "mssql+pymssql://" in url
    assert "db.example.com:1433/TestDB" in url
    assert "usr" in url
    # Password should be URL-encoded
    assert "p%40ssword%23123" in url


def test_database_settings_url_override() -> None:
    db_settings = DatabaseSettings(
        DATABASE_URL="sqlite:///:memory:",
    )
    assert db_settings.get_database_url() == "sqlite:///:memory:"


def test_settings_env_override(monkeypatch: object) -> None:
    assert isinstance(monkeypatch, type(monkeypatch))
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("PERSISTENCE_DRIVER", "mssql")
    mp.setenv("DB_NAME", "OverriddenDB")

    try:
        settings = Settings()
        assert settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL
        assert settings.DB_NAME == "OverriddenDB"
    finally:
        mp.undo()


def test_get_settings_cached() -> None:
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_default_messaging_driver_is_in_memory() -> None:
    settings = Settings()
    assert settings.MESSAGING_DRIVER == MessagingDriver.IN_MEMORY


def test_messaging_settings_rabbitmq_url_construction() -> None:
    msg_settings = MessagingSettings(
        RABBITMQ_HOST="rabbit.example.com",
        RABBITMQ_PORT=5672,
        RABBITMQ_USER="guest",
        RABBITMQ_PASSWORD="p@ssword#123",  # noqa: S106
    )
    url = msg_settings.get_rabbitmq_url()
    assert "amqp://guest:p%40ssword%23123@rabbit.example.com:5672/" == url


def test_messaging_settings_rabbitmq_url_override() -> None:
    msg_settings = MessagingSettings(
        RABBITMQ_URL="amqp://custom:secret@cluster:5672/vhost",
    )
    assert msg_settings.get_rabbitmq_url() == "amqp://custom:secret@cluster:5672/vhost"


def test_messaging_settings_broker_url_canonical_override() -> None:
    msg_settings = MessagingSettings(
        BROKER_URL="amqp://canonical:pass@broker:5672/vhost",
        RABBITMQ_URL="amqp://fallback:pass@fallback:5672/vhost",
    )
    assert msg_settings.get_rabbitmq_url() == "amqp://canonical:pass@broker:5672/vhost"
