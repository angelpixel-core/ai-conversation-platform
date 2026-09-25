# AI Conversation Platform — Slice 1

[![CI Pipeline](https://github.com/angelpixel-core/ai-conversation-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/angelpixel-core/ai-conversation-platform/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checking: Pyright](https://img.shields.io/badge/type_checking-pyright-blue)](https://github.com/microsoft/pyright)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)

A Python reference implementation of the first vertical slice of an AI conversation platform.

## Slice 1

`Create Conversation` is the first domain/application capability. It demonstrates:

- Domain-Driven Design
- Clean / Hexagonal Architecture
- Ports & Adapters
- CQRS-style command handling
- Dependency inversion
- In-memory persistence adapter
- Unit of Work abstraction
- Transactional boundary suitable for a future PostgreSQL + Outbox implementation
- HTTP API with FastAPI
- Structured logging
- HTTP client abstraction
- Telemetry abstraction
- Testable application layer

The implementation intentionally does **not** call an LLM yet. That belongs to Slice 2 (`Send Message` + asynchronous AI processing + streaming).

## Run

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn src.main:app --reload
```

Then:

```bash
curl http://localhost:8000/health
```

Create a conversation:

```bash
curl -X POST http://localhost:8000/conversations \
  -H 'Content-Type: application/json' \
  -d '{"title":"My first AI conversation"}'
```

List it:

```bash
curl http://localhost:8000/conversations
```

Run tests & quality checks:

```bash
make test         # Run unit & integration tests
make coverage     # Run test coverage report
make lint         # Run Ruff linter
make typecheck    # Run Pyright static type checking
make security     # Run Bandit security SAST analysis
make check-all    # Run all QA & security checks
```

## Architecture

```text
interfaces
    ↓
application
    ↓
domain
    ↑
infrastructure adapters
```

The domain and application layers do not depend on FastAPI, SQLAlchemy, Redis, OpenAI/Azure, or other infrastructure details.

## Future slices

1. Create Conversation ← this repository
2. Send Message
3. Async AI processing
4. SSE response streaming
5. Conversation history query + cache
6. Knowledge ingestion
7. Embeddings + pgvector
8. RAG / semantic retrieval
9. Agent tools
10. Cloud deployment / IaC
