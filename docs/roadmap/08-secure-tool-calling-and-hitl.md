# Roadmap de Implementación — Slice 8: Secure Tool Calling, Sandboxed Execution & Human-in-the-Loop (HITL)

Este documento detalla la ruta de desarrollo para la invocación segura de herramientas externas (*Function / Tool Calling*), entornos de ejecución aislados, políticas de aprobación humana (*Human-in-the-Loop*) y auditoría transaccional sobre **Microsoft SQL Server (MSSQL)**, **AnyIO** y **RabbitMQ**.

---

## 🎯 Objetivo del Slice 8

Evolucionar la plataforma de un sistema conversacional puramente reactivo a un motor de agentes autónomos confiables:

1. **Tool Definition & Schema Registry:** Contrato formal para registrar herramientas disponibles para el LLM con especificaciones JSON Schema estrictas derivadas de Pydantic v2.
2. **Políticas de Autorización & Human-in-the-Loop (HITL):** Diferenciar entre herramientas de solo lectura (automáticas) y herramientas con efectos secundarios destructivos o transaccionales (ej. *"reembolsar dinero"*, *"eliminar base de datos"*), suspendiendo la conversación en MSSQL con estado `WAITING_APPROVAL` hasta que un operador humano apruebe o rechace la acción.
3. **Ejecución Segura y Aislada (Sandboxed Runner):** Ejecutar llamadas a APIs o código en entornos acotados con límites estrictos de tiempo (*timeouts*), reintentos y aislamiento de fallos mediante primitivas de **AnyIO**.
4. **Resumed Execution Flow:** Reanudar la conversación de forma transparente una vez que la herramienta devuelve el resultado o se recibe la confirmación humana.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente / Usuario ]
       │  (1. Envía mensaje: "Reembolsa $150 al pedido #4912")
       ▼
[ SendMessageCommandHandler + LLM Client ]
       │  (2. El LLM detecta intención y emite evento 'tool_call: refund_order')
       ▼
[ ToolExecutionPolicyService ]
       │  (3. Evalúa severidad: 'refund_order' requiere autorización humana)
       ├─── Requiere HITL ───┐
       │                     ▼
       │      [ Suspende conversación en MSSQL: status='PENDING_APPROVAL' ]
       │      [ Emite SSE al usuario: 'action_requires_confirmation' ]
       │      [ Operador humano ejecuta POST /approvals/{id}/approve ]
       │                     │
       ▼                     ▼
[ RabbitMQ Topic Exchange ('agent.tool_execution.queue') ]
       │  (4. Despacha ejecución de la herramienta al Sandboxed Worker)
       ▼
[ Tool Execution Worker (src/worker.py) ]
       │  (5. Ejecuta Tool vía AnyIO timeout guard + Adaptador HTTP/SDK)
       │  (6. Persiste resultado de la ejecución en MSSQL)
       ▼
[ Re-engagement Command (Resume Conversation with Tool Result) ]
       │  (7. Reinyecta ToolResult en el prompt del LLM)
       ▼
[ LLM Stream Worker ]
       │  (8. El LLM emite el stream final confirmando la acción al usuario)
       ▼
[ Cliente HTTP (Visualiza respuesta completada) ]

```

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio y Contratos de Herramientas y Aprobaciones

*Entidades de definición de herramientas, llamadas a funciones y estados de aprobación.*

* [x] **Value Objects de Herramientas y Llamadas**
  * Archivo: `src/domain/tools/value_objects/tool_definition.py` (`name`, `description`, `parameters_schema`, `is_deterministic`, `requires_approval`).
  * Archivo: `src/domain/tools/value_objects/tool_call.py` (`call_id`, `tool_name`, `arguments`, `created_at`).
  * Archivo: `src/domain/tools/value_objects/tool_result.py` (`call_id`, `output`, `is_error`, `execution_time_ms`).
* [x] **Entidad de Dominio / Agregado: ToolApprovalRequest (HITL)**
  * Archivo: `src/domain/tools/entities/tool_approval_request.py`
  * Estados: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`.
  * Métodos: `approval.approve(operator_id, justification)`, `approval.reject(operator_id, reason)`.
* [x] **Eventos de Dominio de Herramientas**
  * Archivo: `src/domain/tools/events/tool_events.py`
  * Eventos: `ToolCallRequestedDomainEvent`, `ToolApprovalRequiredDomainEvent`, `ToolExecutionCompletedDomainEvent`, `ToolApprovalResolvedDomainEvent`.
* [x] **Puertos de Persistencia y Ejecución de Herramientas (Driven Ports)**
  * Archivo: `src/domain/tools/ports/tool_registry_port.py` (catálogo y habilitación por tenant).
  * Archivo: `src/domain/tools/ports/tool_approval_repository_port.py`.
  * Archivo: `src/domain/tools/ports/sandboxed_tool_runner_port.py`.
* [x] **Tests Unitarios de Dominio**
  * Archivo: `tests/unit/domain/tools/test_tool_definition.py`
  * Archivo: `tests/unit/domain/tools/test_tool_call_and_result.py`
  * Archivo: `tests/unit/domain/tools/test_tool_approval_request.py`
  * Archivo: `tests/unit/domain/tools/test_tool_events.py`
  * Archivo: `tests/unit/domain/tools/test_tool_ports.py`

---

### Fase 2: Capa de Aplicación (Tool Dispatcher & HITL Handlers)

*Orquestación con AnyIO de la suspensión y reanudación del diálogo.*

* [ ] **Servicio de Evaluación de Políticas de Herramientas**
  * Archivo: `src/application/tools/services/tool_policy_evaluator_service.py`
  * Determina si una llamada se ejecuta automáticamente o se retiene para HITL según las reglas del tenant.
* [ ] **Comando y Handler: Approve Tool Execution (HITL)**
  * Archivo: `src/application/tools/commands/approve_tool_execution.py` (`ApproveToolExecutionCommand`, `ApproveToolExecutionHandler`).
* [ ] **Comando y Handler: Reject Tool Execution (HITL)**
  * Archivo: `src/application/tools/commands/reject_tool_execution.py` (`RejectToolExecutionCommand`, `RejectToolExecutionHandler`).
* [ ] **Worker Command y Handler: Execute Tool in Sandbox**
  * Archivo: `src/application/tools/commands/execute_sandboxed_tool.py` (`ExecuteSandboxedToolCommand`, `ExecuteSandboxedToolHandler`).
* [ ] **Tests Unitarios de Aplicación**
  * Archivo: `tests/unit/application/tools/test_tool_policy_evaluator.py`
  * Archivo: `tests/unit/application/tools/test_approve_tool_execution_handler.py`
  * Archivo: `tests/unit/application/tools/test_reject_tool_execution_handler.py`
  * Archivo: `tests/unit/application/tools/test_execute_sandboxed_tool_handler.py`

---

### Fase 3: Infraestructura MSSQL (Auditoría de Herramientas & Aprobaciones)

*Persistencia relacional de llamadas, parámetros y firmas de aprobación en SQL Server.*

* [ ] **Modelos ORM Físicos en MSSQL**
  * Archivo: `src/infrastructure/persistence/mssql/models.py` (`ToolApprovalModel` y `ToolExecutionAuditModel`).
* [ ] **Mappers y Adaptadores de Repositorio MSSQL**
  * Archivo: `src/infrastructure/persistence/mssql/tool_approval_mapper.py`
  * Archivo: `src/infrastructure/persistence/mssql/mssql_tool_approval_repository.py`
  * Consultas transaccionales con `WITH (ROWLOCK, UPDLOCK)` para evitar que dos operadores aprueben la misma acción simultáneamente.
* [ ] **Adaptador en Memoria para Testing Rápido**
  * Archivo: `src/infrastructure/persistence/in_memory/in_memory_tool_approval_repository.py`
* [ ] **Adaptador de Ejecución Aislada (Sandboxed Runner Adapter)**
  * Archivo: `src/infrastructure/tools/anyio_sandboxed_tool_runner.py`
  * Ejecución con timeout estricto usando `anyio.fail_after()`, límite de memoria y captura de excepciones defensivas.
* [ ] **Migraciones de Esquema T-SQL (Alembic / MSSQL)**
  * Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0005_tools_and_hitl_approvals.py`
* [ ] **Tests de Integración con SQL Server / SQLite**
  * Archivos: `tests/unit/infrastructure/mssql/test_tool_approval_models.py`, `tests/unit/infrastructure/mssql/test_mssql_tool_approval_repository.py`, `tests/unit/infrastructure/tools/test_anyio_sandboxed_tool_runner.py`.

---

### Fase 4: RabbitMQ Pipeline para Ejecución de Herramientas

*Desacoplamiento de llamadas lentas a terceros (webhooks, APIs externas, bases de datos).*

* [ ] **Topología de Exchanges y Queues en RabbitMQ para Herramientas**
  * Archivo: `src/infrastructure/messaging/rabbitmq/tools_topology_config.py`
  * Exchange: `ai_platform.tools` (Topic).
  * Queue principal: `tools.execution.queue`.
  * Dead Letter Queue: `tools.execution.dlq`.
* [ ] **Worker de Ejecución de Herramientas con AnyIO TaskGroups**
  * Archivo: `src/infrastructure/messaging/rabbitmq/anyio_tool_execution_worker.py`
  * Consume solicitudes de ejecución autorizadas, invoca el sandbox y emite el evento de resultado de vuelta a la conversación.
* [ ] **Tests de Integración del Worker de Herramientas**
  * Archivo: `tests/unit/infrastructure/workers/test_anyio_tool_execution_worker.py`
  * Archivo: `tests/unit/infrastructure/messaging/test_tools_topology_config.py`

---

### Fase 5: Interfaces HTTP & Notificaciones en Streaming

*Endpoints de gestión de aprobaciones y eventos SSE de ejecución.*

* [ ] **Esquemas DTO HTTP (Pydantic v2)**
  * Archivo: `src/interfaces/http/tools_schemas.py` (`ToolApprovalDecisionRequest`, `PendingApprovalResponse`, `ToolExecutionAuditResponse`).
* [ ] **Router de Human-in-the-Loop (FastAPI)**
  * Archivo: `src/interfaces/http/approvals_router.py`
  * Endpoint `GET /tenants/{tenant_id}/approvals/pending` (`200 OK`).
  * Endpoint `POST /tenants/{tenant_id}/approvals/{approval_id}/decision` (`200 OK`).
* [ ] **Eventos SSE de Herramientas en Streaming**
  * Modificación del stream en `src/interfaces/http/api.py` para emitir eventos en tiempo real:
    * `event: tool_call_started`
    * `event: tool_approval_required`
* [ ] **Tests de Integración HTTP / E2E**
  * Archivo: `tests/integration/api/test_tool_approval_flow.py`
  * Archivo: `tests/integration/api/test_sandboxed_timeout_error.py`

---

### Fase 6: Ensamble, Container y Documentación de Decisiones

* [ ] **Actualización de `src/container.py` y `src/worker_container.py`**
  * Registro de `SandboxedToolRunnerPort`, `ToolApprovalRepositoryPort` y `ToolPolicyEvaluatorService`.
* [ ] **Documento de Decisión Arquitectónica (ADR)**
  * Archivo: [.agent/architecture/decisions/0007-secure-tool-calling-and-hitl.md](file:///.agent/architecture/decisions/0007-secure-tool-calling-and-hitl.md) (completado y aceptado).
* [ ] **Actualización del Diagrama Vivo**
  * Archivo: [.agent/architecture/system-map.mermaid.md](file:///.agent/architecture/system-map.mermaid.md) (incorporación de Tool Registry, HITL Approvals y Sandboxed Runner).

---

## 🔍 Criterios de Aceptación del Slice 8

1. **Bloqueo Infranqueable de Acciones Críticas:** Ninguna herramienta configurada como `requires_approval=True` se ejecuta de forma autónoma sin una aprobación formal persistida en MSSQL.
2. **Aislamiento y Timeout Resiliente:** Si una herramienta externa se congela o tarda más del umbral configurado (ej. 5 segundos), `anyio.fail_after()` aborta la tarea limpiamente y retorna un `ToolResult` de error al LLM sin tumbar el worker ni la conversación.
3. **Flujo de Reanudación Sin Pérdida de Contexto:** Tras la aprobación humana de una acción pendiente, la conversación se reactiva automáticamente, procesa la respuesta de la herramienta y finaliza el stream con el usuario sin requerir reenvío del mensaje original.
4. **Trazabilidad Total de Acciones Externas:** Cada llamada a una herramienta (argumentos, operador aprobador, tiempo de respuesta y salida generada) queda registrada de forma inmutable en las tablas de auditoría de MSSQL.
