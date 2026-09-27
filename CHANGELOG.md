# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] - 2026-09-27 — Slice 4: Decoupled Event Broker Worker

### Added

- **Multi-Container Orchestration & Operational Interfaces:**
  - Added autonomous `worker` service to `docker-compose.yml` (`chatbot_worker` executing `python -m src.worker`).
  - Added explicit environment variable configuration (`PERSISTENCE_DRIVER=mssql`, `MESSAGING_DRIVER=rabbitmq`) across `api` and `worker` services.
  - Expanded `Makefile` with developer targets: `run-api`, `run-worker`, `db/upgrade`, `db/downgrade`, `stack/up-build`, `stack/status`, and `audit`.
  - Documented design rationale in Architectural Decision Record `ADR 0003` (`.agent/architecture/decisions/0003-decoupled-worker-and-rabbitmq.md`).
  - Updated live system architecture map (`.agent/architecture/system-map.mermaid.md`) and comprehensive documentation (`README.md`).
- **RabbitMQ Resilient Connection & Topology:**
  - Implemented `RabbitMQConnectionManager` (`src/infrastructure/messaging/rabbitmq/rabbitmq_connection_manager.py`) with automatic reconnection and channel acquisition.
  - Implemented `RabbitMQTopologyConfig` (`src/infrastructure/messaging/rabbitmq/rabbitmq_topology_config.py`) declaring durable `ai_platform.events` topic exchange, main durable queue `conversation.llm_processing.queue`, direct DLX `ai_platform.events.dlx`, and DLQ `conversation.llm_processing.dlq`.
  - Added unit test suite `tests/unit/infrastructure/messaging/test_rabbitmq_connection_and_topology.py` with 100% code coverage.
- **RabbitMQ Publisher & Consumer Adapters & Integration:**
  - Implemented `RabbitMQPublisherAdapter` (`src/infrastructure/messaging/rabbitmq/rabbitmq_publisher_adapter.py`) fulfilling `MessageBrokerPort` with persistent delivery, metadata headers, and `passive` declaration support.
  - Implemented `RabbitMQConsumerAdapter` (`src/infrastructure/messaging/rabbitmq/rabbitmq_consumer_adapter.py`) fulfilling `EventConsumerPort` with QoS prefetch count, message dispatching, `passive` queue binding, and Dead-Letter Queue (DLQ) rejection on error.
  - Added unit test suite `tests/unit/infrastructure/messaging/test_rabbitmq_adapters.py` with 100% code coverage.
  - Added integration test suite `tests/integration/infrastructure/messaging/test_rabbitmq_publisher_consumer.py` verifying real end-to-end publish/consume and DLQ routing against a live RabbitMQ broker.
  - Configured `rabbitmq:3-management-alpine` service and volume in `docker-compose.yml`.
- **Autonomous Background Worker & LLM Processing:**
  - Implemented `LlmMessageProcessingWorker` (`src/application/conversations/workers/llm_message_processing_worker.py`) consuming `MessageAppendedDomainEvent`, running model inference via `LlmClientPort`, and persisting assistant replies via `AppendAssistantMessageHandler`.
  - Implemented `WorkerContainer` (`src/worker_container.py`) composition root assembling SQL Server connection, `MssqlUnitOfWork`, `LlmClientPort`, and `RabbitMQConsumerAdapter` without FastAPI dependencies.
  - Implemented autonomous worker process script `src/worker.py` with structured concurrency and POSIX signal handling (`SIGINT`, `SIGTERM`) via `anyio`.
  - Added unit test suites `tests/unit/application/test_llm_message_processing_worker.py`, `tests/unit/test_worker_container.py`, and `tests/unit/test_worker_entrypoint.py` with 100% code coverage.
  - Added full-cycle integration test suite `tests/integration/workers/test_llm_message_processing_worker.py` validating end-to-end user message consumption, LLM completion, SQL Server persistence, and dead-letter queue routing on errors.
  - Added canonical and test templates in `.agent/templates/` for worker handlers and entrypoints.
- **Outbox Publisher Relay & Concurrency:**
  - Extended `OutboxStatus` with `PUBLISHED` state and added `mark_as_published()` to `MssqlOutboxRepository` and `OutboxMessage`.
  - Enhanced `MssqlConversationRepository.add()` to automatically drain and persist domain events to `outbox_messages` as `EventEnvelope` instances in the same ACID transaction.
  - Implemented `OutboxRelayService` (`src/infrastructure/persistence/outbox/outbox_relay_service.py`) performing transactional polling with SQL Server locking hints (`WITH (UPDLOCK, READPAST)`), guaranteed at-least-once delivery to RabbitMQ, and atomic `PUBLISHED` state transitions.
  - Added unit test suite `tests/unit/infrastructure/persistence/test_outbox_relay_service.py` with 100% code coverage.
  - Added concurrency integration test suite `tests/integration/infrastructure/persistence/test_outbox_relay_concurrency.py` verifying race-free competing pollers against live Microsoft SQL Server 2022.
  - Created canonical and test templates in `.agent/templates/` for outbox relay.
- **Messaging Ports & Domain Envelopes:**
  - Implemented `EventEnvelope` (`src/domain/shared/events/event_envelope.py`) value object encapsulating event identifiers, types, payloads, correlation IDs, and ISO-8601 timestamps.
  - Implemented application ports `MessageBrokerPort` and `EventConsumerPort` (`src/application/shared/ports/`).
  - Implemented in-memory testing adapter `InMemoryMessageBroker` (`src/infrastructure/messaging/in_memory/in_memory_message_broker.py`).
  - Added unit test suites for event envelopes, message broker ports, and in-memory broker.
- **Dependencies & Canonical Templates:**
  - Added `aio-pika>=9.4,<10.0` for asynchronous AMQP 0-9-1 broker communication.
  - Created canonical and test templates in `.agent/templates/` for event envelopes, messaging ports, in-memory broker, connection manager, topology configuration, and RabbitMQ adapters.

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
