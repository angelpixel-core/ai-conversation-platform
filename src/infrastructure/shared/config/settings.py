"""Configuration and application settings powered by Pydantic Settings."""

from enum import StrEnum
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentMode(StrEnum):
    """Execution environment mode."""

    LOCAL = "local"
    TEST = "test"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Core application and web server settings."""

    APP_NAME: str = "ai-conversation-platform"
    ENVIRONMENT: EnvironmentMode = EnvironmentMode.LOCAL
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"  # noqa: S104 # nosec B104
    API_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("API_PORT", mode="after")
    @classmethod
    def validate_api_port(cls, v: int) -> int:
        """Validate API port range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"API_PORT must be between 1 and 65535, got {v}")
        return v

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level against standard Python logging levels."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}, got '{v}'")
        return upper_v


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

    @field_validator("DB_PORT", mode="after")
    @classmethod
    def validate_db_port(cls, v: int) -> int:
        """Validate database port range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"DB_PORT must be between 1 and 65535, got {v}")
        return v

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
    BROKER_URL: str | None = None
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

    @field_validator("RABBITMQ_PORT", mode="after")
    @classmethod
    def validate_rabbitmq_port(cls, v: int) -> int:
        """Validate RabbitMQ port range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"RABBITMQ_PORT must be between 1 and 65535, got {v}")
        return v

    def get_broker_url(self) -> str:
        """Return explicit BROKER_URL or construct one with credentials."""
        if self.BROKER_URL:
            return self.BROKER_URL

        safe_pass = quote_plus(self.RABBITMQ_PASSWORD)
        return f"amqp://{self.RABBITMQ_USER}:{safe_pass}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    def get_rabbitmq_url(self) -> str:
        """Return canonical broker URL."""
        return self.get_broker_url()


class TenancySettings(BaseSettings):
    """Multi-tenancy and policy engine configuration."""

    ENABLE_TENANT_MIDDLEWARE: bool = False
    DEFAULT_TENANT_ID: str = "default-tenant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GovernanceSettings(BaseSettings):
    """Enterprise AI Governance and Distributed Observability configuration."""

    ENABLE_OPENTELEMETRY: bool = False
    OTEL_SERVICE_NAME: str = "chatbot-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LlmSettings(BaseSettings):
    """Large Language Model inference and provider settings."""

    LLM_PROVIDER: str = "fake"
    OPENAI_API_KEY: str | None = None  # noqa: S105 # nosec S105
    OPENAI_BASE_URL: str | None = None
    LLM_TIMEOUT_SECONDS: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Settings(
    AppSettings,
    DatabaseSettings,
    MessagingSettings,
    TenancySettings,
    GovernanceSettings,
    LlmSettings,
):
    """Unified application settings with fail-fast validation for drivers."""

    @model_validator(mode="after")
    def validate_fail_fast_drivers(self) -> "Settings":
        """Fail-fast validation ensuring required driver configuration is complete."""
        if self.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
            if not self.DATABASE_URL:
                if not self.DB_SERVER or not self.DB_USER:
                    raise ValueError(
                        "PERSISTENCE_DRIVER='mssql' requires non-empty DB_SERVER and DB_USER"
                    )
        if self.MESSAGING_DRIVER == MessagingDriver.RABBITMQ:
            if not self.BROKER_URL:
                if not self.RABBITMQ_HOST or not self.RABBITMQ_USER:
                    raise ValueError(
                        "MESSAGING_DRIVER='rabbitmq' requires "
                        "non-empty RABBITMQ_HOST and RABBITMQ_USER"
                    )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
