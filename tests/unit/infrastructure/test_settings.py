"""Unit tests for infrastructure settings and configuration."""

import pytest
from pydantic import ValidationError

from src.infrastructure.shared.config.settings import (
    AppSettings,
    DatabaseSettings,
    EnvironmentMode,
    LlmSettings,
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


def test_messaging_settings_broker_url_override() -> None:
    msg_settings = MessagingSettings(
        BROKER_URL="amqp://custom:secret@cluster:5672/vhost",
    )
    assert msg_settings.get_broker_url() == "amqp://custom:secret@cluster:5672/vhost"
    assert msg_settings.get_rabbitmq_url() == "amqp://custom:secret@cluster:5672/vhost"


def test_app_settings_defaults() -> None:
    app_settings = AppSettings()
    assert app_settings.APP_NAME == "ai-conversation-platform"
    assert app_settings.ENVIRONMENT == EnvironmentMode.LOCAL
    assert app_settings.DEBUG is False
    assert app_settings.LOG_LEVEL == "INFO"
    assert app_settings.API_HOST == "0.0.0.0"  # noqa: S104
    assert app_settings.API_PORT == 8000


def test_app_settings_invalid_port_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        AppSettings(API_PORT=99999)
    with pytest.raises(ValidationError):
        AppSettings(API_PORT=0)


def test_app_settings_invalid_log_level_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        AppSettings(LOG_LEVEL="INVALID_LEVEL")


def test_database_settings_invalid_port_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings(DB_PORT=70000)


def test_messaging_settings_invalid_port_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        MessagingSettings(RABBITMQ_PORT=-1)


def test_llm_settings_defaults() -> None:
    llm_settings = LlmSettings()
    assert llm_settings.LLM_PROVIDER == "fake"
    assert llm_settings.OPENAI_API_KEY is None
    assert llm_settings.LLM_TIMEOUT_SECONDS == 30.0


def test_fail_fast_driver_validation_mssql_empty_server() -> None:
    with pytest.raises(ValidationError, match="PERSISTENCE_DRIVER='mssql' requires non-empty"):
        Settings(
            PERSISTENCE_DRIVER=PersistenceDriver.MSSQL,
            DB_SERVER="",
            DATABASE_URL=None,
        )


def test_fail_fast_driver_validation_rabbitmq_empty_host() -> None:
    with pytest.raises(ValidationError, match="MESSAGING_DRIVER='rabbitmq' requires non-empty"):
        Settings(
            MESSAGING_DRIVER=MessagingDriver.RABBITMQ,
            RABBITMQ_HOST="",
            BROKER_URL=None,
        )
