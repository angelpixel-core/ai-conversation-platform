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

---

## 🏛️ Architecture Overview

The system strictly follows the Dependency Rule of Clean Architecture:

```text
               ┌────────────────────────────────────────────────────────┐
               │              Interfaces (Primary Adapters)             │
               │            • FastAPI Router    • CLI Exporter          │
               └──────────────────────────┬─────────────────────────────┘
                                          │ (uses)
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │               Application (CQRS Use Cases)             │
               │   • Commands & Handlers      • Queries & Streamers     │
               │   • Abstract Ports (UoW, LLMClient, EventPublisher)   │
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
               │   • InMemory Repository & UoW   • Outbox Dispatcher   │
               │   • Fake / HTTPX LLM Clients    • Telemetry & Logging  │
               └────────────────────────────────────────────────────────┘
```

> **Key Rule**: The Domain and Application layers have **zero** dependencies on external libraries (no FastAPI, SQLAlchemy, Redis, OpenAI SDK, etc.).

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

### Installation & Run

```bash
# 1. Clone the repository and navigate to the API directory
git clone https://github.com/angelpixel-core/ai-conversation-platform.git
cd ai-conversation-platform/apps/chatbot/service/api

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install project dependencies in editable mode with development extras
make install-dev

# 4. Start the local development server
uvicorn src.main:app --reload
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
make test          # Run all 81 unit & integration tests
make coverage      # Generate detailed test coverage report (>= 90%)
make lint          # Run static code analysis with Ruff
make format-check  # Verify code formatting conformance with Ruff
make format        # Automatically format all source files with Ruff
make typecheck     # Run Pyright strict static type checking
make security      # Run Bandit SAST security vulnerability scan
make docs-build    # Export static OpenAPI schema and standalone ReDoc HTML
make check-all     # Run full quality barrier (format + lint + types + security + tests)
```

---

## 🗺️ Project Roadmap

- [x] **Slice 1:** Create Conversation, DDD Domain Model & Hexagonal Architecture Base
- [x] **Slice 2:** User Messaging, Transactional Outbox Pattern & SSE Token Streaming
- [ ] **Slice 3:** Persistent Storage with PostgreSQL & SQLModel (Transactional Outbox DB)
- [ ] **Slice 4:** Decoupled Event Broker Worker (RabbitMQ / Redis PubSub)
- [ ] **Slice 5:** Conversation History Retrieval & Redis Cache
- [ ] **Slice 6:** Knowledge Ingestion Pipeline & Document Chunking
- [ ] **Slice 7:** Vector Embeddings & pgvector Integration
- [ ] **Slice 8:** Retrieval-Augmented Generation (RAG) Engine
- [ ] **Slice 9:** Autonomous Agent Tool Execution & Function Calling
- [ ] **Slice 10:** Production Containerization & Cloud Infrastructure (IaC)
