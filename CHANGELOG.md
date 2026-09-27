# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — Slice 4: Decoupled Event Broker Worker

### Added
- **RabbitMQ Resilient Connection & Topology:**
  - Implemented `RabbitMQConnectionManager` (`src/infrastructure/messaging/rabbitmq/rabbitmq_connection_manager.py`) with automatic reconnection and channel acquisition.
  - Implemented `RabbitMQTopologyConfig` (`src/infrastructure/messaging/rabbitmq/rabbitmq_topology_config.py`) declaring durable `ai_platform.events` topic exchange, main durable queue `conversation.llm_processing.queue`, direct DLX `ai_platform.events.dlx`, and DLQ `conversation.llm_processing.dlq`.
  - Added unit test suite `tests/unit/infrastructure/messaging/test_rabbitmq_connection_and_topology.py` with 100% code coverage.
- **Messaging Ports & Domain Envelopes:**
  - Implemented `EventEnvelope` (`src/domain/shared/events/event_envelope.py`) value object encapsulating event identifiers, types, payloads, correlation IDs, and ISO-8601 timestamps.
  - Implemented application ports `MessageBrokerPort` and `EventConsumerPort` (`src/application/shared/ports/`).
  - Implemented in-memory testing adapter `InMemoryMessageBroker` (`src/infrastructure/messaging/in_memory/in_memory_message_broker.py`).
  - Added unit test suites for event envelopes, message broker ports, and in-memory broker.
- **Dependencies & Canonical Templates:**
  - Added `aio-pika>=9.4,<10.0` for asynchronous AMQP 0-9-1 broker communication.
  - Created canonical and test templates in `.agent/templates/` for event envelopes, messaging ports, in-memory broker, connection manager, and topology configuration.

---

## [0.3.0] - 2026-09-26 — Slice 3: Persistent Storage with Microsoft SQL Server

### Added
- Microsoft SQL Server 2022 database persistence via `sqlmodel`, `sqlalchemy`, and `pymssql`.
- Alembic database migration environment and initial schema migration in `src/infrastructure/persistence/mssql/migrations/`.
- Relational data models (`ConversationModel`, `MessageModel`, `OutboxMessageModel`) and data mappers (`ConversationDataMapper`).
- `MssqlConversationRepository`, `MssqlOutboxRepository`, and `MssqlUnitOfWork` implementing ACID boundary isolation.
- Integration tests against live MSSQL instance (`tests/integration/persistence/test_mssql_repositories.py`).
- Docker Compose service definition for `mssql` (`mcr.microsoft.com/mssql/server:2022-latest`).

---

## [0.2.0] - 2026-09-25 — Slice 2: Streaming Assistant Messages & Transactional Outbox

### Added
- Server-Sent Events (SSE) streaming endpoint `GET /conversations/{id}/stream`.
- Application queries and commands: `StreamConversationQuery`, `AppendAssistantMessageCommand`, and `SendMessageCommand`.
- LLM driven port `LlmClientPort` with concrete implementations:
  - `FakeLlmClientAdapter` for deterministic local simulation.
  - `HttpxLlmClientAdapter` for upstream SSE stream consumption.
- Transactional Outbox pattern with `InMemoryOutboxRepository` and background dispatcher worker.
- Unit and integration tests for message ingestion, LLM streaming, and outbox dispatching.

---

## [0.1.0] - 2026-09-24 — Slice 1: Core Conversation Domain & In-Memory CQRS

### Added
- Core Domain Model: `Conversation` aggregate root and `Message` value object.
- CQRS application commands: `CreateConversationCommand` and `CreateConversationHandler`.
- Ports and in-memory adapters: `ConversationRepository`, `UnitOfWorkPort`, `InMemoryConversationRepository`, `InMemoryUnitOfWork`.
- FastAPI interfaces: HTTP endpoints for creating and querying conversations.
- CLI script `export-openapi` for generating OpenAPI specification.
- Test suites: Domain unit tests, application handler tests, and interface tests.
