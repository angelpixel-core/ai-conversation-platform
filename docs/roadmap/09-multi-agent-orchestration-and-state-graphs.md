# Roadmap de Implementación — Slice 9: Multi-Agent Orchestration, Hierarchical Supervisor & State Graphs

Este documento detalla la ruta de desarrollo para la orquestación de sistemas multi-agente, máquinas de estado dirigidas (*State Graphs / Directed Acyclic Graphs*), agentes supervisores jerárquicos y persistencia de checkpoints transaccionales sobre **Microsoft SQL Server 2022 (MSSQL)**, **AnyIO Structured Concurrency** y **RabbitMQ**.

---

## 🎯 Objetivo del Slice 9

Permitir la resolución de problemas complejos dividiendo la carga de trabajo entre agentes especializados (ej. *Investigador RAG*, *Redactor*, *Validador de Código*, *Auditor HITL*):

1. **Grafo de Estado Declarativo (State Graph Engine):** Motor desacoplado para modelar flujos de trabajo como grafos dirigidos donde los nodos son agentes especialistas o transformaciones funcionales, y las aristas representan transiciones condicionales evaluadas sobre el estado acumulado.
2. **Supervisor Jerárquico (Orchestrator Agent):** Un agente coordinador que analiza la petición global del usuario, descompone el plan en subtareas y delega la ejecución al agente especialista idóneo según la política del tenant.
3. **Persistencia Transaccional de Checkpoints en MSSQL 2022:** Guardar instantáneas completas e inmutables del estado del grafo (*State Snapshots / Time-Travel Debugging*) en SQL Server con aislamiento multi-tenant estricto (`tenant_id`), permitiendo auditoría, pausa de flujos de larga duración y reanudación determinista ante fallos.
4. **Structured Concurrency con AnyIO:** Ejecución paralela de subagentes independientes mediante `anyio.create_task_group()` (ej. consultar múltiples fuentes o validar simultáneamente) con barreras de sincronización limpias y propagación de cancelación sin corrutinas huérfanas.
5. **Sinergia con Slices Previos:**
   - **Slice 6 (Multi-Tenancy & Budgets):** Aislamiento estricto por `tenant_id` y validación de presupuestos/cuotas antes de bifurcar subagentes.
   - **Slice 7 (Hybrid RAG):** El subagente investigador consulta `HybridRetrieverService` e inyecta fuentes citadas en el snapshot global.
   - **Slice 8 (Secure Tool Calling & HITL):** Si un subagente invoca una herramienta que requiere aprobación (`requires_approval=True`), el grafo transiciona a `WAITING_APPROVAL`, suspende su ejecución en un checkpoint en MSSQL y se reanuda tras la intervención del operador humano.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente / Usuario ]
       │  (1. Solicita tarea compleja: "Audita este contrato, compáralo con normativas y ejecuta acción")
       ▼
[ Application Layer: Graph Orchestrator Service ]
       │  (2. Inicializa WorkflowInstance y StateSnapshot en MSSQL con status='RUNNING')
       ▼
[ Supervisor Agent Node ]
       │  (3. Evalúa estado y decide delegar en paralelo a 2 especialistas)
       ▼
[ AnyIO TaskGroup: Parallel Sub-Agents Dispatch ]
       ├─── Delegación 1 ───> [ RabbitMQ: 'agent.researcher.queue' ]
       │                                     │
       │                                     ▼
       │                       [ Researcher Agent Worker (Consume RAG Slice 7) ]
       │
       └─── Delegación 2 ───> [ RabbitMQ: 'agent.specialist.queue' ]
                                             │
                                             ▼
                               [ Specialist Agent Worker (Ejecuta Sandbox/HITL Slice 8) ]
       │
       ▼  (Ambos completan -> Sincronización AnyIO)
[ Reducer / Merger Node (State Reducer Service) ]
       │  (4. Consolida estados parciales en el StateSnapshot global sin colisión de claves)
       │  (5. Guarda Checkpoint intermedio en MSSQL: version=2 con ROWLOCK, UPDLOCK)
       ▼
[ Synthesis & Quality Reviewer Node ]
       │  (6. Genera respuesta unificada final y valida consistencia de negocio)
       ▼
[ Outbox / Streaming SSE Adapter ]
       │  (7. Emite stream consolidado al usuario: 'event: agent_handoff', 'event: subagent_completed')
       ▼
[ Cliente HTTP (Visualiza progreso por subagente y respuesta final integrada) ]
```

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio y Contratos de Grafos y Redes de Agentes

*Entidades de grafo, value objects de estado inmutable, roles de agentes y puertos abstractos.*

* [x] **Value Objects de Grafo y Nodos**
  * Archivo: `src/domain/agents/value_objects/workflow_id.py` (`WorkflowId`).
  * Archivo: `src/domain/agents/value_objects/checkpoint_id.py` (`CheckpointId`).
  * Archivo: `src/domain/agents/value_objects/agent_role.py` (`AgentRole`: SUPERVISOR, SPECIALIST, CRITIC, SUMMARIZER).
  * Archivo: `src/domain/agents/value_objects/graph_edge.py` (`GraphEdge`: `source_node`, `target_node`, `condition_expression`).
  * Archivo: `src/domain/agents/value_objects/state_snapshot.py` (`StateSnapshot`: `checkpoint_id`, `tenant_id`, `workflow_id`, `current_node`, `state_data`, `version`, `status`).

* [x] **Entidades de Dominio de Workflow y Grafo**
  * Archivo: `src/domain/agents/entities/workflow_graph.py` (Definición declarativa de nodos, aristas, puntos de entrada y fin).
  * Archivo: `src/domain/agents/entities/workflow_instance.py` (Agregado raíz que administra el ciclo de vida del flujo, transiciones de estado e invariantes multi-tenant).

* [x] **Eventos de Dominio de Multi-Agente**
  * Archivo: `src/domain/agents/events/workflow_events.py`
  * Eventos: `WorkflowStartedDomainEvent`, `SubAgentTaskDelegatedDomainEvent`, `CheckpointSavedDomainEvent`, `WorkflowApprovalRequiredDomainEvent`, `WorkflowCompletedDomainEvent`.

* [x] **Excepciones de Dominio**
  * Archivo: `src/domain/agents/exceptions.py`
  * Excepciones: `WorkflowNotFoundError`, `InvalidGraphTransitionError`, `GraphCycleDetectedError`, `SubAgentExecutionError`.

* [x] **Puertos de Persistencia de Checkpoints y Catálogo de Agentes (Driven Ports)**
  * Archivo: `src/domain/agents/ports/workflow_checkpoint_repository_port.py`.
  * Archivo: `src/domain/agents/ports/agent_catalog_port.py`.

* [x] **Tests Unitarios de Dominio**
  * Archivo: `tests/unit/domain/agents/test_workflow_graph.py`
  * Archivo: `tests/unit/domain/agents/test_workflow_instance.py`
  * Archivo: `tests/unit/domain/agents/test_state_snapshot.py`
  * Archivo: `tests/unit/domain/agents/test_agent_role.py`
  * Archivo: `tests/unit/domain/agents/test_graph_edge.py`
  * Archivo: `tests/unit/domain/agents/test_workflow_events.py`
  * Archivo: `tests/unit/domain/agents/test_workflow_ports.py`

---

### Fase 2: Capa de Aplicación (Graph Execution Engine & Handlers)

*Motor de avance de nodos, coordinación con AnyIO TaskGroups y sincronización paralela.*

* [x] **Motor de Ejecución de Grafos (Graph Execution Engine)**
  * Archivo: `src/application/agents/services/graph_execution_engine.py`
  * Control del ciclo de vida del grafo, evaluación de condiciones de salida y orquestación con AnyIO TaskGroups.

* [x] **Comando: Start Workflow Execution**
  * Comando DTO: `src/application/agents/commands/start_workflow_command.py`
  * Command Handler: `src/application/agents/commands/start_workflow_command_handler.py`

* [x] **Comando: Resume Workflow from Checkpoint**
  * Comando DTO: `src/application/agents/commands/resume_workflow_command.py`
  * Command Handler: `src/application/agents/commands/resume_workflow_command_handler.py`

* [x] **Servicio de Reducción y Fusión de Estados (State Reducer)**
  * Archivo: `src/application/agents/services/state_reducer_service.py` (combina resultados concurrentes sin colisión de claves).

* [x] **Tests Unitarios de Aplicación**
  * Archivo: `tests/unit/application/agents/test_graph_execution_engine.py`
  * Archivo: `tests/unit/application/agents/test_state_reducer_service.py`
  * Archivo: `tests/unit/application/agents/test_workflow_command_handlers.py`

---

### Fase 3: Infraestructura MSSQL 2022 (Checkpoints & Historial de Grafo)

*Modelos SQLModel en `models.py`, mapeadores DDD, repositorio transaccional y migraciones Alembic.*

* [x] **Modelos ORM Físicos en SQLModel (`src/infrastructure/persistence/mssql/models.py`)**
  * `WorkflowInstanceModel` (tabla `workflow_instances`): `id`, `tenant_id` (indexado), `name`, `status`, `current_node`, `created_at`, `updated_at`.
  * `WorkflowCheckpointModel` (tabla `workflow_checkpoints`): `id`, `tenant_id` (indexado), `workflow_id` (indexado), `version`, `node_id`, `state_json`, `created_at`.
  * Índices compuestos: `(tenant_id, id)` y `(tenant_id, workflow_id, version)`.

* [x] **Mapeador DDD (Workflow Mapper)**
  * Archivo: `src/infrastructure/persistence/mssql/workflow_mapper.py`

* [x] **Adaptador de Repositorio de Checkpoints en MSSQL**
  * Archivo: `src/infrastructure/persistence/mssql/mssql_workflow_checkpoint_repository.py`
  * Control de concurrencia pesimista con T-SQL `WITH (ROWLOCK, UPDLOCK)` para evitar doble reanudación o sobreescritura de checkpoints.
  * Archivo: `src/infrastructure/persistence/mssql/in_memory_workflow_checkpoint_repository.py` (adaptador en memoria para tests ultrarrápidos).

* [x] **Migración Alembic T-SQL**
  * Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0006_multi_agent_checkpoints.py`

* [x] **Tests de Repositorio y Persistencia**
  * Archivo: `tests/unit/infrastructure/mssql/test_workflow_models.py`
  * Archivo: `tests/unit/infrastructure/mssql/test_workflow_mapper.py`
  * Archivo: `tests/unit/infrastructure/mssql/test_mssql_workflow_checkpoint_repository.py`
  * Archivo: `tests/unit/infrastructure/mssql/test_in_memory_workflow_checkpoint_repository.py`

---

### Fase 4: RabbitMQ Pipeline para Delegación de Sub-Agentes

*Distribución asíncrona de subtareas a colas especializadas y workers desacoplados.*

* [x] **Topología de Exchanges y Queues para Agentes en RabbitMQ**
  * Archivo: `src/infrastructure/messaging/rabbitmq/multi_agent_topology_config.py`
  * Exchange: `ai_platform.agents` (Topic Exchange).
  * Queues dedicadas: `agent.supervisor.queue`, `agent.specialist.queue`, `agent.reviewer.queue` con enlaces a DLQ `agent.dead_letter.queue`.

* [x] **Worker de Ejecución de Subagentes con AnyIO**
  * Archivo: `src/infrastructure/messaging/rabbitmq/anyio_subagent_worker.py`
  * Bounded concurrency con `anyio.Semaphore`, consumo asíncrono y despacho de eventos de resultado parcial.

* [x] **Tests Unitarios e Integración del Worker Multi-Agente**
  * Archivo: `tests/unit/infrastructure/messaging/test_anyio_subagent_worker.py`

---

### Fase 5: Interfaces HTTP & Visualización de Progreso en Tiempo Real

*Endpoints REST para control de workflows y eventos SSE con la actividad de cada subagente.*

* [ ] **Esquemas DTO HTTP (Pydantic v2)**
  * Archivo: `src/interfaces/http/agents_schemas.py` (`StartWorkflowRequest`, `WorkflowStateResponse`, `WorkflowCheckpointResponse`, `AgentActivityEventSchema`).

* [ ] **Router de Orquestación Multi-Agente (FastAPI)**
  * Archivo: `src/interfaces/http/routers/workflows_router.py`
  * `POST /tenants/{tenant_id}/workflows` (`202 Accepted`).
  * `GET /tenants/{tenant_id}/workflows/{workflow_id}/checkpoints` (`200 OK`).
  * `POST /tenants/{tenant_id}/workflows/{workflow_id}/resume` (`200 OK`).

* [ ] **Eventos SSE de Transición de Nodos en Streaming**
  * Integración en `src/interfaces/http/api.py` para emitir eventos de coordinación en tiempo real:
    * `event: agent_handoff` (data: `{"from": "supervisor", "to": "researcher", "step": 1}`)
    * `event: subagent_completed` (data: `{"agent": "researcher", "summary": "Found 3 references"}`)
    * `event: checkpoint_saved` (data: `{"workflow_id": "...", "version": 2}`)

* [ ] **Tests de Integración HTTP / E2E**
  * Archivo: `tests/integration/api/test_multi_agent_workflow_flow.py`
  * Archivo: `tests/integration/api/test_workflow_resume_endpoint.py`

---

### Fase 6: Ensamble, Container, Plantillas y Documentación de Decisiones

* [ ] **Actualización de Contenedores de Dependencias**
  * Archivos: `src/container.py` y `src/worker_container.py`
  * Inyección de `WorkflowCheckpointRepositoryPort`, `GraphExecutionEngine` y servicios de orquestación.

* [ ] **Extracción de Plantillas Canónicas (`.agent/templates/`)**
  * `workflow_graph.tt.py` y `test_workflow_graph.tt.py`
  * `workflow_instance.tt.py` y `test_workflow_instance.tt.py`
  * `graph_execution_engine.tt.py` y `test_graph_execution_engine.tt.py`
  * `anyio_subagent_worker.tt.py` y `test_anyio_subagent_worker.tt.py`

* [ ] **Documento de Decisión Arquitectónica (ADR 0008)**
  * Archivo: `.agent/architecture/decisions/0008-multi-agent-orchestration-and-state-graphs.md`.

* [ ] **Actualización del Diagrama Vivo del Sistema**
  * Archivo: `.agent/architecture/system-map.mermaid.md` (incorporación del Graph Engine, State Checkpoints en MSSQL y topología de colas de subagentes).

* [ ] **Exportación de OpenAPI y ReDoc**
  * Ejecución de `make docs-build` para regenerar `public/openapi.json` y `public/index.html`.

---

## 🔍 Criterios de Aceptación del Slice 9

1. **Determinismo y Resiliencia en Checkpointing:** Si el proceso worker colapsa en mitad del flujo, el sistema es capaz de reanudar el grafo exactamente desde el último checkpoint persistido en MSSQL sin reiniciar la ejecución de subagentes ya completados.
2. **Sincronización Concurrente Segura (AnyIO):** Las llamadas a subagentes paralelos se ejecutan mediante `anyio.create_task_group()`; si uno falla de forma irrecuperable, la cancelación cooperativa aborta las tareas hermanas sin dejar llamadas activas colgadas contra el proveedor de LLM.
3. **Aislamiento Multi-Tenant en Grafos:** Los estados de flujo, datos intermedios y checkpoints de un tenant están completamente blindados y segregados a nivel de repositorio y base de datos respecto a los demás inquilinos.
4. **Trazabilidad Completa del Razonamiento:** El cliente puede reconstruir mediante el endpoint de checkpoints la secuencia exacta de decisiones tomadas por el supervisor, qué agentes participaron y cómo se sintetizó el resultado final.
