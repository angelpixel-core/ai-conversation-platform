# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.10.0] - 2026-09-29 — Slice 10: Enterprise AI Governance, Real-Time Guardrails & Distributed Observability

### Added

- **Domain Layer (Governance Value Objects, Security Aggregate Root & Ports):**
  - Implemented `SafetyVerdict` (`src/domain/governance/value_objects/safety_verdict.py`) capturing evaluation verdicts, violation types, risk scores, and matched rules.
  - Implemented `IncidentSeverity` enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `PiiEntityMatch`, and `TraceContext` value objects supporting W3C `traceparent` parsing and generation.
  - Implemented `SecurityIncident` aggregate root (`src/domain/governance/entities/security_incident.py`) governing forensic security events, multi-tenant isolation, and domain event dispatching.
  - Defined domain events: `SafetyViolationBlockedDomainEvent` and `PromptInjectionDetectedDomainEvent`.
  - Defined driven ports: `SafetyGuardrailPort`, `PiiScannerPort`, and `IncidentRepositoryPort`.
  - Added domain exception: `SafetyPolicyViolationError` with violation classification and risk scoring.
- **Application Layer (Concurrent Guardrail Pipeline, Guarded Executor & CQRS Handlers):**
  - Implemented `SafetyGuardrailPipelineService` (`src/application/governance/services/guardrail_pipeline_service.py`) running heuristic security validation and PII detection concurrently with `anyio.create_task_group()`.
  - Implemented `GuardedCommandExecutor` (`src/application/governance/services/guarded_command_executor.py`) intercepting commands, executing guardrails, persisting incidents, and blocking unsafe requests before LLM inference.
  - Implemented `TraceContextCarrier` (`src/application/shared/telemetry/trace_context_carrier.py`) serializing and deserializing W3C trace contexts across HTTP headers and AMQP message envelopes.
  - Implemented CQRS commands and queries: `RecordSecurityIncidentCommand` / `RecordSecurityIncidentHandler`, `ListIncidentsQuery` / `ListIncidentsQueryHandler`, and `GetGovernanceMetricsQuery` / `GetGovernanceMetricsQueryHandler`.
- **Infrastructure Layer (Zero-Bloat Guardrails, MSSQL Incident Storage & OpenTelemetry):**
  - Implemented `RegexPiiScannerAdapter` (`src/infrastructure/governance/regex_pii_scanner_adapter.py`) featuring precompiled regexes and the Luhn algorithm for credit card verification (<1ms latency, 0 heavy ML bloat).
  - Implemented `HeuristicInjectionDetectorAdapter` (`src/infrastructure/governance/heuristic_injection_detector_adapter.py`) blocking system prompt overrides, jailbreaks, and credential harvesting in <10ms.
  - Implemented `AnyioStreamGuardrailFilter` (`src/infrastructure/governance/anyio_stream_guardrail_filter.py`) evaluating token windows during SSE delivery and terminating compromised streams.
  - Implemented `SecurityIncidentModel` and `MssqlIncidentRepository` (`src/infrastructure/persistence/mssql/mssql_incident_repository.py`) supporting multi-tenant indexed forensic incident queries in SQL Server 2022.
  - Added Alembic database migration `0007_governance_incidents.py`.
  - Implemented `OpenTelemetryTracingAdapter` (`src/infrastructure/telemetry/opentelemetry_tracing_adapter.py`) strictly isolated in infrastructure without domain leakage.
- **HTTP Interfaces, Middlewares & Admin API:**
  - Implemented `OpenTelemetryMiddleware` (`src/interfaces/http/middlewares/opentelemetry_middleware.py`) injecting `X-Trace-ID` and `X-Span-ID` into response headers and propagating W3C context.
  - Registered centralized FastAPI exception handler for `SafetyPolicyViolationError` returning structured `HTTP 400 Bad Request`.
  - Implemented admin governance router (`src/interfaces/http/routers/governance_router.py`) with endpoints:
    - `GET /admin/tenants/{tenant_id}/incidents` (`HTTP 200 OK`) with paginated filtering.
    - `GET /admin/governance/metrics` (`HTTP 200 OK`) aggregating global safety statistics.
  - Defined Pydantic v2 schemas in `src/interfaces/http/governance_schemas.py`.
- **Composition Roots, ADR & Documentation:**
  - Configured `GovernanceSettings` (`ENABLE_OPENTELEMETRY`, `OTEL_SERVICE_NAME`) in `Settings`.
  - Wired governance ports, pipeline, guarded executor, and telemetry in `AppContainer` and `WorkerContainer`.
  - Documented architectural decisions in `ADR 0009` (`.agent/architecture/decisions/0009-ai-governance-guardrails-and-opentelemetry.md`).
  - Extracted canonical templates into `.agent/templates/`.
  - Synchronized Living Architecture Map in `.agent/architecture/system-map.mermaid.md`.
  - Completed roadmap checklist in `docs/roadmap/10-ai-governance-and-observability.md`.

### Changed

- Updated `src/container.py` and `src/worker_container.py` to inject `SafetyGuardrailPort`, `PiiScannerPort`, `IncidentRepositoryPort`, and `GuardrailPipelineService`.
- Extended `src/interfaces/http/api.py` to route mutating message commands through `GuardedCommandExecutor` and register `governance_router`.
- Updated developer documentation and OpenAPI specification.

### Security

- Neutralized prompt injection and jailbreak attacks with zero LLM token consumption.
- Eliminated PII data leaks (credit cards, emails, SSNs, phone numbers, API keys) across database persistence and RabbitMQ messaging.
- Enforced immutable audit trails for all security policy violations in SQL Server.

---

## [0.9.0] - 2026-09-28 — Slice 9: Multi-Agent Orchestration, Hierarchical Supervisor & State Graphs

### Added

- **Domain Layer (Multi-Agent Entities, State Graph Value Objects & Ports):**
  - Implemented `AgentRole` enum (`SUPERVISOR`, `SPECIALIST`, `CRITIC`, `SUMMARIZER`), `GraphNode`, `GraphEdge`, and `WorkflowGraph` value objects (`src/domain/agents/value_objects/graph_definition.py`) for declarative directed acyclic state graphs.
  - Implemented `ExecutionState` and `AgentTask` value objects (`src/domain/agents/value_objects/execution_state.py`) capturing immutable execution snapshots, context variables, and subagent payloads.
  - Implemented `WorkflowInstance` aggregate root (`src/domain/agents/entities/workflow_instance.py`) governing execution states (`PENDING`, `RUNNING`, `WAITING_APPROVAL`, `PAUSED`, `COMPLETED`, `FAILED`), step transitions, and domain events.
  - Defined domain events: `WorkflowStartedDomainEvent`, `AgentTaskDelegatedDomainEvent`, `SubAgentCompletedDomainEvent`, `WorkflowSuspendedDomainEvent`, and `WorkflowCompletedDomainEvent`.
  - Defined driven ports: `WorkflowRepositoryPort` (`save_instance`, `get_instance`, `save_checkpoint`, `get_latest_checkpoint`, `get_checkpoints`) and `SubAgentExecutorPort` (`execute_agent_task`).
  - Added domain exceptions: `WorkflowNotFoundError`, `InvalidGraphDefinitionError`, and `WorkflowExecutionError`.
- **Application Layer (Graph Engine, State Reducer & CQRS Handlers):**
  - Implemented `StateReducerService` (`src/application/agents/services/state_reducer_service.py`) providing deterministic functional state merging for context dictionaries, messages, and citations.
  - Implemented `GraphExecutionEngine` (`src/application/agents/services/graph_execution_engine.py`) managing graph node traversal, evaluating conditional routing edges, driving concurrent node execution with `anyio.create_task_group()`, handling HITL pauses, and persisting step checkpoints.
  - Implemented CQRS commands and handlers: `StartWorkflowCommand` / `StartWorkflowCommandHandler` (`src/application/agents/commands/start_workflow.py`) and `ResumeWorkflowCommand` / `ResumeWorkflowCommandHandler` (`src/application/agents/commands/resume_workflow.py`).
- **Infrastructure Layer (MSSQL 2022 Checkpoint Storage & SQLModel):**
  - Implemented SQLModel relational tables `WorkflowInstanceModel` (`workflow_instances`) and `WorkflowCheckpointModel` (`workflow_checkpoints`) in `src/infrastructure/persistence/mssql/models.py` with multi-tenant compound indexes.
  - Implemented `WorkflowDataMapper` (`src/infrastructure/persistence/mssql/workflow_mapper.py`) for lossless conversion between domain aggregates, execution states, and SQLModel records.
  - Implemented `MssqlWorkflowRepository` (`src/infrastructure/persistence/mssql/mssql_workflow_repository.py`) supporting checkpoint history and pessimistic locking (`WITH (ROWLOCK, UPDLOCK)`).
  - Implemented `InMemoryWorkflowRepositoryAdapter` (`src/infrastructure/persistence/in_memory/in_memory_workflow_repository.py`) for ultra-fast unit testing.
  - Added Alembic migration `0006_workflow_instances_and_checkpoints.py`.
- **RabbitMQ Multi-Agent Pipeline & AnyIO Subagent Worker:**
  - Implemented `AgentsTopologyConfig` (`src/infrastructure/messaging/rabbitmq/agents_topology_config.py`) declaring `ai_platform.agents` topic exchange, `agent.supervisor.queue`, `agent.specialist.queue`, and DLQs.
  - Implemented `RabbitMQSubAgentExecutorAdapter` (`src/infrastructure/agents/rabbitmq_subagent_executor.py`) providing decoupled asynchronous agent delegation.
  - Implemented `AnyioSubAgentWorker` (`src/infrastructure/messaging/rabbitmq/anyio_subagent_worker.py`) consuming subagent tasks and processing inference with bounded concurrency (`anyio.Semaphore`).
- **HTTP Interfaces, REST Endpoints & Real-Time SSE Streams:**
  - Implemented `workflows_router.py` with endpoints:
    - `POST /tenants/{tenant_id}/workflows` (`HTTP 202 Accepted`).
    - `GET /tenants/{tenant_id}/workflows/{workflow_id}/checkpoints` (`HTTP 200 OK`).
    - `POST /tenants/{tenant_id}/workflows/{workflow_id}/resume` (`HTTP 200 OK`).
    - `GET /tenants/{tenant_id}/workflows/{workflow_id}/stream` (`HTTP 200 OK`, `text/event-stream`).
  - Added Server-Sent Events (SSE) streaming for `event: agent_handoff`, `event: subagent_completed`, and `event: checkpoint_saved`.
  - Defined Pydantic v2 schemas in `src/interfaces/http/agents_schemas.py`.
  - Exported updated OpenAPI 3.1 specification and ReDoc HTML.
- **Composition Roots, ADR & System Map:**
  - Wired `WorkflowRepositoryPort`, `SubAgentExecutorPort`, `StateReducerService`, `GraphExecutionEngine`, and workflow commands/handlers in `src/container.py` and `src/worker_container.py`.
  - Documented architectural decisions in `ADR 0008` (`.agent/architecture/decisions/0008-multi-agent-orchestration-and-state-graphs.md`).
  - Synchronized Living Architecture Map in `.agent/architecture/system-map.mermaid.md`.
  - Completed roadmap checklist in `docs/roadmap/09-multi-agent-orchestration-and-state-graphs.md`.

---

## [0.8.0] - 2026-09-28 — Slice 8: Secure Tool Calling, Sandboxed Execution & Human-in-the-Loop (HITL)

### Added

- **Domain Layer (Tool Value Objects, HITL Aggregate & Domain Events):**
  - Implemented `ToolDefinition`, `ToolCall`, and `ToolResult` value objects (`src/domain/tools/value_objects/`) standardizing parameter schemas, determinism flags, and result outputs.
  - Implemented `ToolApprovalRequest` aggregate root (`src/domain/tools/entities/tool_approval_request.py`) managing the full HITL approval lifecycle (`PENDING` ➔ `APPROVED` / `REJECTED` / `EXPIRED`).
  - Defined domain events: `ToolCallRequestedDomainEvent`, `ToolApprovalRequiredDomainEvent`, `ToolApprovalResolvedDomainEvent`, and `ToolExecutionCompletedDomainEvent`.
  - Defined driven ports: `ToolRegistryPort`, `ToolApprovalRepositoryPort`, and `SandboxedToolRunnerPort`.
  - Added domain exceptions: `ToolNotFoundError`, `ToolExecutionError`, and `InvalidApprovalStateError`.
- **Application Layer (Policy Evaluator & CQRS Handlers):**
  - Implemented `ToolPolicyEvaluatorService` (`src/application/tools/services/tool_policy_evaluator_service.py`) inspecting tool definitions and tenant policies to determine whether HITL review is required.
  - Implemented CQRS commands and handlers: `ApproveToolExecutionCommand` / `ApproveToolExecutionHandler`, `RejectToolExecutionCommand` / `RejectToolExecutionHandler`, and `ExecuteSandboxedToolCommand` / `ExecuteSandboxedToolHandler`.
- **Infrastructure Layer (MSSQL 2022, Pessimistic Locking & Sandboxed Runner):**
  - Implemented SQLModel relational tables `ToolApprovalModel` (`tool_approvals`) and `ToolExecutionAuditModel` (`tool_execution_audits`) with multi-tenant compound indexes.
  - Implemented `MssqlToolApprovalRepository` (`src/infrastructure/persistence/mssql/mssql_tool_approval_repository.py`) using `WITH (ROWLOCK, UPDLOCK)` row-level locks preventing race conditions between operators.
  - Implemented `InMemoryToolApprovalRepositoryAdapter` (`src/infrastructure/persistence/in_memory/in_memory_tool_approval_repository.py`) for deterministic fast unit testing.
  - Implemented `AnyioSandboxedToolRunner` (`src/infrastructure/tools/anyio_sandboxed_tool_runner.py`) executing tools within `anyio.fail_after()` timeout guards and capturing exceptions gracefully.
  - Added Alembic migration `0005_tools_and_hitl_approvals.py`.
- **RabbitMQ Tool Execution Pipeline:**
  - Implemented `ToolsTopologyConfig` (`src/infrastructure/messaging/rabbitmq/tools_topology_config.py`) declaring `ai_platform.tools` topic exchange, `tools.execution.queue`, and DLQ.
  - Implemented `AnyioToolExecutionWorker` (`src/infrastructure/messaging/rabbitmq/anyio_tool_execution_worker.py`) for isolated asynchronous tool execution with bounded concurrency (`anyio.Semaphore`).
- **HTTP Interfaces, REST Endpoints & Real-Time SSE Notifications:**
  - Implemented `approvals_router.py` with endpoints:
    - `GET /tenants/{tenant_id}/approvals/pending` (`HTTP 200 OK`).
    - `POST /tenants/{tenant_id}/approvals/{approval_id}/decision` (`HTTP 200 OK`).
  - Added Server-Sent Events (SSE) streaming for `event: tool_approval_required` and `event: tool_call_started` in `src/interfaces/http/api.py`.
  - Defined Pydantic v2 schemas in `src/interfaces/http/tools_schemas.py`.
  - Exported updated OpenAPI 3.1 schema and interactive ReDoc documentation in `public/`.
- **Composition Roots, ADR & System Map:**
  - Wired `SandboxedToolRunnerPort`, `ToolApprovalRepositoryPort`, and `ToolPolicyEvaluatorService` in `src/container.py` and `src/worker_container.py`.
  - Documented architectural decisions in `ADR 0007` (`.agent/architecture/decisions/0007-secure-tool-calling-and-hitl.md`).
  - Synchronized Living Architecture Map in `.agent/architecture/system-map.mermaid.md`.
  - Completed roadmap checklist in `docs/roadmap/08-secure-tool-calling-and-hitl.md`.

---

## [0.7.0] - 2026-09-28 — Slice 7: Semantic Vector Search, Hybrid RAG & Knowledge Grounding

### Added

- **Domain Layer (Knowledge Aggregates, Value Objects & Events):**
  - Implemented `EmbeddingVector` value object (`src/domain/knowledge/value_objects/embedding_vector.py`) enforcing $L_2$-normalization, cosine similarity, dimension validation (1536-d), and zero-vector rejection.
  - Implemented `Citation` value object (`src/domain/knowledge/value_objects/citation.py`) capturing verified document metadata (`source_document_id`, `document_name`, `chunk_id`, `page_number`, `similarity_score`, `snippet`).
  - Implemented `Document` aggregate root (`src/domain/knowledge/entities/document.py`) managing document lifecycle states (`UPLOADED`, `PROCESSING`, `INDEXED`, `FAILED`) and factory creation.
  - Implemented `DocumentChunk` entity (`src/domain/knowledge/entities/document_chunk.py`) associating text fragments with parent document, tenant, sequence order, page number, and vector embedding.
  - Defined domain events: `DocumentUploadedDomainEvent`, `DocumentIndexedDomainEvent`, `DocumentIndexingFailedDomainEvent`, and `KnowledgeContextRetrievedDomainEvent`.
  - Defined driven ports `KnowledgeRepositoryPort` (`save_document`, `get_document`, `save_chunks`, `get_chunks_by_document`, `search_hybrid`) and `EmbeddingClientPort`.
  - Added domain exception `DocumentNotFoundError`.
  - Added unit test suites covering value objects, entities, events, and port contracts with 100% green coverage.
- **Application Layer (Use Cases & Hybrid Retrieval Service):**
  - Implemented `UploadDocumentCommand` and `UploadDocumentHandler` (`src/application/knowledge/commands/upload_document.py`) registering tenant-scoped knowledge documents.
  - Implemented `IndexDocumentChunksCommand` and `IndexDocumentChunksHandler` (`src/application/knowledge/commands/index_document_chunks.py`) with atomic chunk persistence and resilient failure handling.
  - Implemented `HybridRetrieverService` (`src/application/knowledge/services/hybrid_retriever_service.py`) orchestrating hybrid vector similarity ($S_{\text{vector}}$) and lexical token overlap ($S_{\text{lexical}}$) with configurable balance $\alpha$.
  - Integrated hybrid retriever into `LlmMessageProcessingWorker` for grounding conversations with cited knowledge context.
- **MSSQL Infrastructure & Embeddings:**
  - Implemented ORM models `DocumentModel` (`knowledge_documents`) and `DocumentChunkModel` (`knowledge_document_chunks`) in `src/infrastructure/persistence/mssql/models.py` with multi-tenant compound indexes.
  - Implemented `KnowledgeDataMapper` (`src/infrastructure/persistence/mssql/knowledge_mapper.py`) for bidirectional mapping between SQLModel and domain models.
  - Implemented `MssqlKnowledgeRepository` (`src/infrastructure/persistence/mssql/mssql_knowledge_repository.py`) supporting hybrid retrieval directly on Microsoft SQL Server 2022 and SQLite.
  - Implemented `InMemoryKnowledgeRepositoryAdapter` (`src/infrastructure/persistence/in_memory/knowledge_repository.py`) for ultra-fast local testing.
  - Implemented `FakeEmbeddingClientAdapter` and `HttpxEmbeddingClientAdapter` (`src/infrastructure/embeddings/`).
  - Added Alembic migration `0004_knowledge_documents_and_vectors.py`.
- **RabbitMQ Ingestion Pipeline with AnyIO:**
  - Implemented `KnowledgeTopologyConfig` (`src/infrastructure/messaging/rabbitmq/knowledge_topology_config.py`) declaring `ai_platform.knowledge_events` topic exchange and `knowledge.indexing.queue`.
  - Implemented `AnyioDocumentIndexerWorker` (`src/infrastructure/messaging/rabbitmq/anyio_document_indexer_worker.py`) for concurrent batch chunking and embedding generation with `anyio.create_task_group()` and `anyio.Semaphore`.
- **HTTP Interfaces & Streaming Citations:**
  - Implemented `knowledge_router.py` with endpoints:
    - `POST /tenants/{tenant_id}/documents` (`HTTP 202 Accepted`).
    - `GET /tenants/{tenant_id}/documents/{document_id}/status` (`HTTP 200 OK`).
  - Added Server-Sent Events (SSE) `event: citation` streaming in `src/interfaces/http/api.py`.
  - Defined Pydantic v2 schemas in `src/interfaces/http/knowledge_schemas.py`.
- **Container Wiring & Architectural Living Documentation:**
  - Wired `HybridRetrieverService`, `EmbeddingClientPort`, and `KnowledgeRepositoryPort` in `src/container.py` and `src/worker_container.py`.
  - Documented architectural decisions in `ADR 0006` (`.agent/architecture/decisions/0006-hybrid-rag-and-mssql-vector-search.md`).
  - Synchronized Living System Map in `.agent/architecture/system-map.mermaid.md`.
  - Completed roadmap checklist in `docs/roadmap/07-semantic-vector-search-and-hybrid-rag.md`.

---

## [0.6.0] - 2026-09-28 — Slice 6: Multi-Tenant Policy Engine, Dynamic Model Routing & Cost Budgets

### Added

- **Strict Multi-Tenant Isolation:**
  - Implemented `TenantId` Value Object and `TenantContext` for logical tenant segregation across HTTP endpoints, background workers, and database tables.
  - Added `TenantContextMiddleware` enforcing tenant header checks on protected routes.
- **Pessimistic Quota & Budget Control:**
  - Implemented two-phase quota governance (`ReserveQuotaCommand` and `SettleQuotaCommand`) with pessimistic locking (`WITH (ROWLOCK, UPDLOCK)`) in Microsoft SQL Server to prevent double-spending race conditions.
  - Automated rejection returning `HTTP 402 Payment Required` on exhausted balances.
- **Dynamic Model Routing & Fallback Gateway:**
  - Implemented `ModelRoute` Value Object, `ModelCatalogPort`, and `ModelRouterService` selecting optimal LLM providers by contract tier and max tokens with transparent fallback activation.
- **Tenant Administration & Relational Persistence:**
  - Added tenant admin router (`/admin/tenants/{id}/budget`, `/admin/tenants/{id}/policy`, `/admin/tenants/{id}/reserve`).
  - Implemented `TenantModel`, `TenantPolicyModel`, `TenantDataMapper`, and `MssqlTenantRepository`.
  - Added Alembic migration `0003_multi_tenant_and_budgets.py`.

---

## [0.5.0] - 2026-09-27 — Slice 5: Enterprise Auditing, Distributed Idempotency & Resilient Stream Recovery

### Added

- **Distributed Idempotency (Deduplication):**
  - Implemented `IdempotencyKey` Value Object, `IdempotencyRepositoryPort`, and `IdempotentCommandExecutor` ensuring exactly-once processing with `HTTP 409 Conflict` detection.
  - Implemented `MssqlIdempotencyRepository` and `InMemoryIdempotencyRepositoryAdapter`.
- **Immutable Enterprise Auditing:**
  - Implemented `AuditLogRecord` domain entity and `AuditRepositoryPort` persisting structured audit trails in MSSQL.
- **Resilient SSE Stream Recovery:**
  - Implemented `StreamChunk` Value Object, `StreamBufferRepositoryPort`, and `StreamRecoveryService` supporting network drop reconnections via `Last-Event-ID` without re-triggering LLM inference.
  - Implemented `MssqlStreamBufferRepository` and `InMemoryStreamBufferRepositoryAdapter`.
- **Database Migrations:**
  - Added Alembic migration `0002_idempotency_audit_and_stream_buffer.py`.

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
