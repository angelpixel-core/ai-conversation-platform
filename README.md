# AI Conversation Platform API

[![CI Pipeline](https://github.com/angelpixel-core/ai-conversation-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/angelpixel-core/ai-conversation-platform/actions/workflows/ci.yml)
[![OpenAPI / ReDoc Docs](https://img.shields.io/badge/OpenAPI-ReDoc%20Docs-85EA2D?logo=openapi-initiative&logoColor=black)](https://angelpixel-core.github.io/ai-conversation-platform/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checking: Pyright](https://img.shields.io/badge/type_checking-pyright-blue)](https://github.com/microsoft/pyright)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)

Production-grade Python reference platform for AI-powered conversational services. Built strictly following **Clean Architecture**, **Domain-Driven Design (DDD)**, **CQRS**, the **Transactional Outbox Pattern**, and **Server-Sent Events (SSE)** streaming.

---

## 🚀 Implemented Capabilities (Vertical Slices)

### Slice 1: Conversation Management & Hexagonal Foundation

- **Domain-Driven Design**: `Conversation` Aggregate Root with lifecycle invariants and `ConversationCreatedDomainEvent`.
- **Ports & Adapters (Hexagonal)**: Strict isolation of business logic from framework details; zero external dependencies in the domain.
- **CQRS Commands**: `CreateConversationCommand` and `CreateConversationHandler`.
- **In-Memory Persistence & Unit of Work**: Atomicity and transaction boundary abstraction ready for relational databases.
- **Primary HTTP Adapter**: FastAPI application with OpenAPI spec generation and automated static documentation via ReDoc.

### Slice 2: Messaging, Outbox Pattern & SSE Real-Time Streaming

- **Message Value Object**: Invariant enforcement on conversation history (sequence order, user/assistant role transitions, message length).
- **Domain Events**: `MessageAppendedDomainEvent` and `AssistantResponseCompletedDomainEvent`.
- **Transactional Outbox Pattern**:
  - `OutboxMessage` & `InMemoryOutboxRepository` for atomic event persistence within the same unit of work.
  - Asynchronous `OutboxDispatcher` background worker for reliable decoupled event dispatching.
- **LLM Streaming Adapters (Ports & Adapters)**:
  - `FakeLlmClientAdapter`: Deterministic test adapter with simulated token streaming latency without external API keys.
  - `HttpxLlmClientAdapter`: Production-ready async client connecting to OpenAI-compatible SSE endpoints (`/chat/completions`), supporting keep-alive filtering and `[DONE]` termination.
- **Reactive Streaming Endpoints**:
  - `POST /conversations/{id}/messages`: Ingests user input synchronously (<50ms) and queues domain events.
  - `GET /conversations/{id}/stream`: Real-time token-by-token streaming using Server-Sent Events (`text/event-stream`).

### Slice 3: Persistent Storage with Microsoft SQL Server & SQLModel
- **Enterprise Relational Persistence**: Microsoft SQL Server 2022 engine integration via `SQLModel` / `SQLAlchemy` with transactional `pymssql` driver.
- **Relational Models & Schemas**: Dedicated relational mappings for `conversations`, `messages`, and `outbox_messages` with cascading foreign keys and optimized indexes.
- **ACID Unit of Work & Repository**: `MssqlUnitOfWork`, `MssqlConversationRepository`, and `MssqlOutboxRepository` guaranteeing aggregate state and domain events commit atomically.
- **Database Migrations**: Alembic migration suite configured with single-command `make db/upgrade` and `make db/downgrade`.

### Slice 4: Decoupled Event Broker Worker (RabbitMQ & Autonomous Worker)
- **AMQP 0-9-1 Messaging Broker**: `RabbitMQConnectionManager`, `RabbitMQTopologyConfig`, `RabbitMQPublisherAdapter`, and `RabbitMQConsumerAdapter` with resilient reconnect handling via `aio-pika`.
- **Transactional Outbox Relay**: `OutboxRelayService` extracting pending events from SQL Server with non-blocking row locks (`WITH (UPDLOCK, READPAST)`) and publishing to RabbitMQ (`conversation.events` topic exchange).
- **Autonomous Background Worker**: Standalone background daemon (`src/worker.py` and `WorkerContainer`) consuming from `conversation.llm_processing.queue`, invoking LLM inference, and appending assistant responses.
- **Dead Letter Queue (DLQ) & Fault Tolerance**: Non-recoverable processing errors are safely rejected to `conversation.llm_processing.dlq` via `conversation.dlx` without message loss.
- **Structured Concurrency & Graceful Shutdown**: Native `anyio` task groups and POSIX signal management (`SIGINT`/`SIGTERM`) for safe termination.
- **Multi-Container Orchestration**: Full `docker-compose.yml` configuration (API, Worker, SQL Server 2022, RabbitMQ) and dedicated `Makefile` developer targets.

---

## 🏛️ Architecture Overview

The system strictly follows the Dependency Rule of Clean Architecture:

```text
               ┌────────────────────────────────────────────────────────┐
               │              Interfaces (Primary Adapters)             │
               │   • FastAPI Router  • CLI Exporter  • Worker Process   │
               └──────────────────────────┬─────────────────────────────┘
                                          │ (uses)
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │               Application (CQRS Use Cases)             │
               │   • Commands & Handlers      • Queries & Streamers     │
               │   • Worker Use Cases         • Abstract Domain Ports   │
               └──────────────────────────┬─────────────────────────────┘
                                          │ (uses)
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │                Domain (Core Business Rules)            │
               │   • Conversation Aggregate   • Message Value Object    │
               │   • Domain Events            • Domain Exceptions       │
               └──────────────────────────▲─────────────────────────────┘
                                          │ (implements ports)
               ┌──────────────────────────┴─────────────────────────────┐
               │             Infrastructure (Secondary Adapters)        │
               │   • MSSQL & InMemory Repos   • Outbox Relay Service    │
               │   • RabbitMQ Publisher/Consumer • HTTPX LLM Clients    │
               └────────────────────────────────────────────────────────┘
```

> **Key Rule**: The Domain and Application layers have **zero** dependencies on external libraries (no FastAPI, SQLAlchemy, RabbitMQ, OpenAI SDK, etc.).

---

## 🔌 API Endpoints

| Method | Path | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health status check | `200 OK` |
| `POST` | `/conversations` | Create a new conversation aggregate | `201 Created` |
| `POST` | `/conversations/{id}/messages` | Append a user message (triggers Outbox event) | `200 OK` |
| `GET` | `/conversations/{id}/stream` | Stream AI response tokens via Server-Sent Events | `200 OK` (`text/event-stream`) |
| `GET` | `/docs` | Interactive Swagger UI API documentation | `200 OK` |
| `GET` | `/redoc` | Interactive ReDoc documentation | `200 OK` |

---

## ⚡ Quickstart

### Prerequisites

- Python 3.12+
- Virtual environment (`venv`)
- Docker & Docker Compose (for SQL Server and RabbitMQ)

### 1. Local Development

```bash
# Clone the repository and navigate to the API directory
git clone https://github.com/angelpixel-core/ai-conversation-platform.git
cd ai-conversation-platform/apps/chatbot/service/api

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode with development tools
make install-dev

# Apply database migrations
make db/upgrade

# Start the local FastAPI server
make run-api

# In a separate terminal, start the background worker process
make run-worker
```

### 2. Multi-Container Stack (Docker Compose)

```bash
# Launch the full stack (API + Worker + MSSQL + RabbitMQ)
make stack/up-build

# Check running container health and status
make stack/status

# Tear down the stack
make stack/down
```

---

## 🧪 Usage Examples (cURL)

### 1. Check Health

```bash
curl -s http://localhost:8000/health | jq
```

### 2. Create a Conversation

```bash
CONV_ID=$(curl -s -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Demo AI Architecture"}' | jq -r '.id')

echo "Created Conversation ID: $CONV_ID"
```

### 3. Send a Message

```bash
curl -s -X POST "http://localhost:8000/conversations/${CONV_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "Explain the Outbox Pattern in 3 bullet points."}' | jq
```

### 4. Stream AI Response via Server-Sent Events (SSE)

```bash
curl -N "http://localhost:8000/conversations/${CONV_ID}/stream"
```

---

## 🛠️ Developer Tooling & Verification

A comprehensive `Makefile` provides one-command access to all quality barriers:

```bash
make test          # Run all 192 unit & integration tests
make coverage      # Generate detailed test coverage report (>= 90%)
make lint          # Run static code analysis with Ruff
make format-check  # Verify code formatting conformance with Ruff
make format        # Automatically format all source files with Ruff
make typecheck     # Run Pyright strict static type checking
make security      # Run Bandit SAST security vulnerability scan
make audit         # Run dependency vulnerability audit with pip-audit
make docs-build    # Export static OpenAPI schema and standalone ReDoc HTML
make run-api       # Run FastAPI server in reload mode (uvicorn)
make run-worker    # Run autonomous LLM background worker process
make db/upgrade    # Apply pending database migrations with Alembic
make db/downgrade  # Rollback last database migration with Alembic
make stack/up      # Launch multi-container stack via Docker Compose
make stack/up-build# Rebuild and launch multi-container stack via Docker Compose
make stack/status  # Inspect Docker Compose service status
make stack/down    # Stop and tear down Docker Compose stack
make check-all     # Run full quality barrier (format + lint + types + security + tests)
```

---

## 🗺️ Project Roadmap

- [x] **Slice 1:** Create Conversation, DDD Domain Model & Hexagonal Architecture Base
- [x] **Slice 2:** User Messaging, Transactional Outbox Pattern & SSE Token Streaming
- [x] **Slice 3:** Persistent Storage with Microsoft SQL Server & SQLModel (Transactional Outbox DB)
- [x] **Slice 4:** Decoupled Event Broker Worker (RabbitMQ Pub/Sub & Autonomous Background Worker)
- [ ] **Slice 5:** Conversation History Retrieval & Redis Cache
- [ ] **Slice 6:** Knowledge Ingestion Pipeline & Document Chunking
- [ ] **Slice 7:** Vector Embeddings & pgvector Integration
- [ ] **Slice 8:** Retrieval-Augmented Generation (RAG) Engine
- [ ] **Slice 9:** Autonomous Agent Tool Execution & Function Calling
- [ ] **Slice 10:** Production Containerization & Cloud Infrastructure (IaC)
