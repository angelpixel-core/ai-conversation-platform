# Roadmap de Implementación — Slice 5: Enterprise Auditing, Distributed Idempotency & Resilient Stream Recovery

Este documento detalla la ruta de desarrollo, auditoría distribuida, garantías de idempotencia y recuperación de streams desconectados para el quinto slice vertical de **ai-conversation-platform**, adaptado al entorno empresarial establecido sobre **Microsoft SQL Server 2022 (`pymssql` / SQLModel)**, **AnyIO (Structured Concurrency)** y **RabbitMQ**.

---

## 🎯 Objetivo del Slice 5

Dotar al sistema de resiliencia y trazabilidad de grado financiero/enterprise:

1. **Idempotencia Distribuida (Deduplication):** Prevenir procesamiento redundante de mensajes o cobros de tokens ante reintentos de red del cliente o del broker RabbitMQ.
2. **Auditoría Transaccional en MSSQL:** Registro inmutable de eventos de auditoría y consumo de tokens usando tablas optimizadas en Microsoft SQL Server con transacciones aisladas.
3. **Resilient Stream Recovery:** Si el cliente pierde la conexión HTTP/SSE mientras el LLM sigue respondiendo en el worker, el buffer generado se persiste en MSSQL y el cliente puede reconectarse solicitando el stream desde el último token recibido (`Last-Event-ID`).
4. **Structured Concurrency con AnyIO:** Consolidación de primitivas estructuradas de **AnyIO** (`TaskGroup`, cancelación segura, backpressure y streams en memoria) agnósticas al runtime.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente HTTP ]
       │  (1. Request con Header 'Idempotency-Key' y opcional 'Last-Event-ID')
       ▼
[ FastAPI + AnyIO TaskGroup ]
       │  (2. Verifica Idempotency Key en MSSQL antes de procesar)
       ▼
[ MSSQL DB (Idempotency Records & Conversations) ]
       │  (3. Transacción atómica: Conversation + Outbox en MSSQL)
       ▼
[ Outbox Poller (AnyIO Loop) ]
       │  (4. Despacha evento hacia RabbitMQ Topic Exchange)
       ▼
[ RabbitMQ (AMQP Topic Broker) ]
       │  (5. Worker consume con Ack manual bajo AnyIO TaskGroup)
       ▼
[ Worker Process (src/worker.py) ]
       │  (6. Genera stream LLM -> Almacena buffer incremental en MSSQL)
       ▼
[ Stream Recovery Buffer (MSSQL / Memory Cache) ]
```

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio y Contratos de Idempotencia, Auditoría & Stream Recovery

*Reglas puras para detección de duplicados, tokens de auditoría y chunks versionados.*

- [x] **Value Objects de Idempotencia y Secuencia de Chunks**
  - Archivo: `src/domain/conversations/value_objects/idempotency_key.py`
  - Template canónico: `.agent/templates/domain/value_objects/idempotency_key.tt.py`
  - Test template: `.agent/templates/domain/value_objects/test_idempotency_key.tt.py`
  - Archivo: `src/domain/conversations/value_objects/stream_chunk.py` (`chunk_id`, `sequence_number`, `content`, `is_final`, `created_at`)
  - Template canónico: `.agent/templates/domain/value_objects/stream_chunk.tt.py`
  - Test template: `.agent/templates/domain/value_objects/test_stream_chunk.tt.py`

- [x] **Entidad de Dominio: Audit Log Record**
  - Archivo: `src/domain/audit/audit_log_entity.py`
  - Template canónico: `.agent/templates/domain/entities/audit_log_record.tt.py`
  - Test template: `.agent/templates/domain/entities/test_audit_log_record.tt.py`

- [x] **Puertos de Persistencia de Idempotencia, Auditoría y Stream Buffer (Driven Ports)**
  - Archivo: `src/application/shared/ports/idempotency_repository_port.py`
  - Template canónico: `.agent/templates/application/shared/ports/idempotency_repository_port.tt.py`
  - Test template: `.agent/templates/application/shared/ports/test_idempotency_repository_port.tt.py`
  - Archivo: `src/domain/audit/ports/audit_repository_port.py`
  - Template canónico: `.agent/templates/domain/ports/audit_repository_port.tt.py`
  - Test template: `.agent/templates/domain/ports/test_audit_repository_port.tt.py`
  - Archivo: `src/application/shared/ports/stream_buffer_repository_port.py`
  - Template canónico: `.agent/templates/application/shared/ports/stream_buffer_repository_port.tt.py`
  - Test template: `.agent/templates/application/shared/ports/test_stream_buffer_repository_port.tt.py`

- [x] **Adaptadores en Memoria para Testing (In-Memory Adapters)**
  - Archivo: `src/infrastructure/persistence/in_memory/in_memory_idempotency_repository.py`
  - Template canónico: `.agent/templates/infrastructure/persistence/in_memory/in_memory_idempotency_repository.tt.py`
  - Test template: `.agent/templates/infrastructure/persistence/in_memory/test_in_memory_idempotency_repository.tt.py`
  - Archivo: `src/infrastructure/persistence/in_memory/in_memory_audit_repository.py`
  - Template canónico: `.agent/templates/infrastructure/persistence/in_memory/in_memory_audit_repository.tt.py`
  - Test template: `.agent/templates/infrastructure/persistence/in_memory/test_in_memory_audit_repository.tt.py`

- [x] **Tests Unitarios de Dominio**
  - Archivo: `tests/unit/domain/test_idempotency_key.py`
  - Archivo: `tests/unit/domain/test_stream_chunk_sequence.py`
  - Archivo: `tests/unit/domain/test_audit_log_record.py`

---

### Fase 2: Capa de Aplicación (AnyIO-Powered CQRS & Pipelines)

*Orquestadores y ejecutores basados en concurrencia estructurada.*

- [ ] **Pipeline / Ejecutor de Idempotencia para Commands**
  - Archivo: `src/application/shared/idempotency/idempotent_command_executor.py` (bloqueo atómico, ejecución y almacenamiento de resultado previo).
  - Template canónico: `.agent/templates/application/shared/idempotency/idempotent_command_executor.tt.py`
  - Test template: `.agent/templates/application/shared/idempotency/test_idempotent_command_executor.tt.py`

- [ ] **Servicio de Recuperación de Stream (Stream Recovery)**
  - Archivo: `src/application/conversations/services/stream_recovery_service.py` (reemite chunks perdidos desde el sequence_number solicitado mediante AnyIO).
  - Template canónico: `.agent/templates/application/services/stream_recovery_service.tt.py`
  - Test template: `.agent/templates/application/services/test_stream_recovery_service.tt.py`

- [ ] **Query: Resume Stream by Last-Event-ID**
  - Query DTO: `src/application/conversations/queries/resume_stream_query.py`
  - Handler: `src/application/conversations/queries/resume_stream_query_handler.py`

- [ ] **Tests Unitarios de Aplicación con AnyIO**
  - Archivo: `tests/unit/application/test_idempotent_command_executor.py`
  - Archivo: `tests/unit/application/test_resume_stream_query_handler.py`
  - Archivo: `tests/unit/application/test_stream_recovery_service.py`

---

### Fase 3: Infraestructura MSSQL (SQL Server & SQLModel Extensions)

*Extensión del stack relacional existente con `pymssql` y SQLModel.*

- [ ] **Modelos Físicos de SQL Server (Tablas Empresariales)**
  - Archivo: `src/infrastructure/persistence/mssql/models.py` (extender con `IdempotencyRecordModel`, `AuditLogModel`, `StreamBufferChunkModel`).

- [ ] **Adaptadores de Repositorio MSSQL**
  - Repositorio Idempotencia: `src/infrastructure/persistence/mssql/idempotency_repository.py`
  - Repositorio Auditoría: `src/infrastructure/persistence/mssql/audit_repository.py`
  - Repositorio Buffer Chunks: `src/infrastructure/persistence/mssql/stream_buffer_repository.py`
  - Unit of Work MSSQL: extender `src/infrastructure/persistence/mssql/unit_of_work.py` para incluir repositorios de auditoría, idempotencia y buffer dentro del contexto transaccional.

- [ ] **Migraciones de Esquema T-SQL (Alembic / MSSQL)**
  - Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0002_enterprise_auditing_and_idempotency.py`

- [ ] **Tests de Integración con SQL Server Real**
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_idempotency_repository.py`
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_audit_repository.py`
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_stream_buffer_repository.py`

---

### Fase 4: Integración en Worker y Auditoría de Consumo LLM

*Integración de streaming resiliente e idempotencia en el Worker autónomo.*

- [ ] **Worker con Buffer de Streaming Incremental**
  - Archivo: `src/application/conversations/workers/llm_message_processing_worker.py` (actualizar para emitir chunks con `sequence_number` a `StreamBufferRepositoryPort` mientras se recibe el stream del LLM).
  - Registro de auditoría con tokens reales consumidos al completar la inferencia.

- [ ] **Idempotencia en Consumo de Mensajes AMQP**
  - Garantizar deduplicación a nivel de mensaje en el worker si RabbitMQ reenvía un evento previamente procesado (`ack` diferido o redelivery).

- [ ] **Tests de Integración Worker + Buffer de Streaming**
  - Archivo: `tests/integration/workers/test_worker_streaming_buffer.py`

---

### Fase 5: Interfaces HTTP & Headers Empresariales

*Validación de idempotencia y reconexión SSE en FastAPI.*

- [ ] **Middleware / Dependencia de Idempotencia**
  - Archivo: `src/interfaces/http/dependencies/idempotency_dependency.py` (inspecciona y valida header `Idempotency-Key`).
  - Template canónico: `.agent/templates/interfaces/http/idempotency_dependency.tt.py`
  - Test template: `.agent/templates/interfaces/http/test_idempotency_dependency.tt.py`

- [ ] **Router de Streaming con Soporte `Last-Event-ID`**
  - Archivo: `src/interfaces/http/messages_router.py` (inspecciona header estándar SSE `Last-Event-ID` para reanudar el flujo sin regenerar la respuesta).
  - Template canónico: `.agent/templates/interfaces/http/resumable_sse_endpoint.tt.py`
  - Test template: `.agent/templates/interfaces/http/test_resumable_sse_endpoint.tt.py`

- [ ] **Tests de Integración HTTP / E2E**
  - Archivo: `tests/integration/api/test_idempotent_requests.py`
  - Archivo: `tests/integration/api/test_stream_reconnection.py`

---

### Fase 6: Ensamble, Container y Documentación de Decisiones

- [ ] **Actualización de Inyección de Dependencias**
  - Archivo: `src/container.py` (registro de `IdempotencyRepository`, `AuditRepository`, `StreamBufferRepository` y `StreamRecoveryService`).
  - Archivo: `src/worker_container.py` (inyección de repositorios de buffer y auditoría).

- [ ] **Documento de Decisión Arquitectónica (ADR)**
  - Archivo: `.agent/architecture/decisions/0004-distributed-idempotency-and-stream-recovery.md`

- [ ] **Actualización del Diagrama Vivo**
  - Archivo: `.agent/architecture/system-map.mermaid.md`

---

## 🔍 Criterios de Aceptación del Slice 5

1. **Deduplicación Garantizada:** Enviar dos peticiones simultáneas con el mismo `Idempotency-Key` resulta en una sola ejecución del LLM; la segunda petición espera o retorna exactamente la misma respuesta almacenada en MSSQL con status `200 OK`.
2. **Reanudación de Streams (Reconnection):** Si el cliente interrumpe la lectura a los 50 tokens y se reconecta pasando `Last-Event-ID: 50`, el endpoint le transmite a partir del token 51 en adelante sin cobrar doble inferencia ni relanzar el modelo.
3. **Structured Concurrency Verificada:** Ninguna corrutina o tarea de fondo queda huérfana en el worker ni en la API; todas se gestionan bajo el árbol estructurado de `anyio.create_task_group()`.
4. **Trazabilidad y Auditoría Inmutable:** Cada interacción, llamada y token consumido queda registrado en la tabla `audit_logs` vinculada a la transacción de base de datos.
