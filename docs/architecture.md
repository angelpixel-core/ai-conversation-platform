---
id: architecture
aliases: []
tags: []
---

# Architecture Notes

## Boundaries

### Domain
Contains business concepts and invariants. It has no framework dependencies.

### Application
Contains use cases and ports. It orchestrates domain behavior and defines
transactional boundaries.

### Infrastructure
Contains adapters for persistence, HTTP clients, logging, telemetry and,
later, LLM/embedding/vector-store providers.

### Interfaces
Contains delivery mechanisms such as HTTP.

## Unit of Work + Outbox

The intended production transaction is:

```text
BEGIN
  mutate aggregate
  persist aggregate
  persist outbox event
COMMIT
```

This gives a single ACID boundary for state and the event that must eventually
be published.

The current slice keeps the abstractions and a local in-memory implementation.
A PostgreSQL adapter should be added before claiming production-grade ACID
semantics.

## Why no LLM yet?

Slice 1 establishes the conversation aggregate and application boundary.
Slice 2 can add:

```text
SendMessageCommand
  -> persist user message
  -> publish MessageSubmitted
  -> async AI worker
  -> LLM port
  -> stream response
  -> persist assistant message
```

SSE is the initial streaming candidate because it is simpler than introducing
WebSockets for a one-way token stream.
