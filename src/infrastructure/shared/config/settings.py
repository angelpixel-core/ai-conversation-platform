"""Configuration and application settings powered by Pydantic Settings."""

from enum import StrEnum
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class PersistenceDriver(StrEnum):
    """Supported persistence backend drivers."""

    IN_MEMORY = "in_memory"
    MSSQL = "mssql"


class DatabaseSettings(BaseSettings):
    """Database connection and driver configuration."""

    PERSISTENCE_DRIVER: PersistenceDriver = PersistenceDriver.IN_MEMORY
    DB_SERVER: str = "localhost"
    DB_PORT: int = 1433
    DB_NAME: str = "ChatbotDB"
    DB_USER: str = "sa"
    DB_PASSWORD: str = "YourStrong@Password123"  # noqa: S105 # nosec S105
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """Return the database URL or construct one for MSSQL with URL-safe credentials."""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        safe_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mssql+pymssql://{self.DB_USER}:{safe_password}@"
            f"{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}"
        )


class MessagingDriver(StrEnum):
    """Supported event messaging backend drivers."""

    IN_MEMORY = "in_memory"
    RABBITMQ = "rabbitmq"


class MessagingSettings(BaseSettings):
    """Message broker and event streaming configuration."""

    MESSAGING_DRIVER: MessagingDriver = MessagingDriver.IN_MEMORY
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"  # noqa: S105 # nosec S105
    RABBITMQ_URL: str | None = None
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_EXCHANGE: str = "ai_platform.events"
    RABBITMQ_QUEUE: str = "conversation.llm_processing.queue"
    RABBITMQ_DLX_EXCHANGE: str = "ai_platform.events.dlx"
    RABBITMQ_DLQ: str = "conversation.llm_processing.dlq"
    RABBITMQ_ROUTING_KEY: str = "conversation.message.appended"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_rabbitmq_url(self) -> str:
        """Return explicit RABBITMQ_URL or construct one with URL-safe credentials."""
        if self.RABBITMQ_URL:
            return self.RABBITMQ_URL

        safe_pass = quote_plus(self.RABBITMQ_PASSWORD)
        return f"amqp://{self.RABBITMQ_USER}:{safe_pass}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"


class Settings(DatabaseSettings, MessagingSettings):
    """Unified application settings."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
