# ADR 0008: Orquestación Multi-Agente, Supervisor Jerárquico y Grafos de Estado con Checkpointing en MSSQL

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-28
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 9 — Multi-Agent Orchestration, Hierarchical Supervisor & State Graphs

---

## 1. Contexto y Problemática

A medida que la plataforma incorpora recuperación de conocimiento híbrida (RAG, Slice 7) y ejecución de herramientas con intervención humana (HITL, Slice 8), los requerimientos de negocio evolucionan desde turnos conversacionales simples hacia **problemas complejos de múltiples pasos** (ej. auditorías legales, análisis cruzado de normativas, investigación asistida y validación automatizada de código).

Tratar de resolver estos escenarios mediante un único prompt monolítico o un único agente presenta limitaciones severas:

1. **Pérdida de Foco y Alucinación por Sobrecarga de Contexto:** Un modelo generalista pierde precisión si se le exige razonar, consultar múltiples fuentes documentales, generar herramientas y sintetizar respuestas en una sola inferencia.
2. **Falta de Paralelismo y Concurrencia Estructurada:** Tareas independientes (como investigar en 3 colecciones de documentos simultáneamente o validar sintaxis y seguridad en paralelo) deben ejecutarse concurrentemente sin bloquear el hilo principal y con cancelación limpia si una rama falla.
3. **Pérdida de Progreso y Falta de Resiliencia ante Fallos:** Si un flujo de 5 pasos se interrumpe en el paso 4 debido a un timeout o caída del worker, reiniciar el proceso completo desperdicia presupuesto de tokens y degrada la experiencia del usuario. Se requiere una estrategia de **Checkpointing transaccional** que capture instantáneas inmutables del estado (*State Snapshots / Time-Travel Debugging*).
4. **Gobierno, Aislamiento Multi-Tenant y Auditoría:** Cada paso, delegación entre agentes y resultado parcial debe quedar indexado por `tenant_id` y persistido de manera inmutable en **Microsoft SQL Server 2022**, con protección de concurrencia pesimista para evitar que dos procesos reanuden el mismo workflow simultáneamente.

---

## 2. Decisión de Diseño

Se establece una arquitectura basada en Clean Architecture, DDD, CQRS, State Graphs dirigidos, concurrencia estructurada con AnyIO y persistencia de checkpoints en MSSQL 2022:

### 2.1. Modelo de Dominio de Grafos y Redes de Agentes (DDD)

1. **Value Objects (`src/domain/agents/value_objects/`):**
   - `WorkflowId`: Identificador único y tipado de la instancia de flujo de trabajo.
   - `CheckpointId`: Identificador inmutable de la instantánea de estado.
   - `AgentRole`: Enumeración con los roles del sistema: `SUPERVISOR`, `SPECIALIST`, `CRITIC`, `SUMMARIZER`.
   - `GraphEdge`: Representa una transición dirigida entre nodos (`source_node`, `target_node`) con una expresión condicional opcional (`condition_expression`).
   - `StateSnapshot`: Representa una captura inmutable del estado del flujo en un instante dado: `checkpoint_id`, `tenant_id`, `workflow_id`, `current_node`, diccionario inmutable de datos (`state_data: dict`), número de versión monotónico incremental (`version: int`) y estado de ejecución (`status`).
2. **Entidades y Agregados (`src/domain/agents/entities/`):**
   - `WorkflowGraph`: Entidad que modela el grafo dirigido declarativo (nodos, aristas, punto de entrada y condiciones de finalización). Valida aciclicidad y alcanzabilidad de nodos finales.
   - `WorkflowInstance`: Agregado Raíz que administra el ciclo de vida de la ejecución (`RUNNING`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED`), asegurando invariantes multi-tenant (`tenant_id`), emisión de eventos de dominio e incremento estricto de versiones de checkpoint.
3. **Eventos de Dominio (`src/domain/agents/events/workflow_events.py`):**
   - `WorkflowStartedDomainEvent`: Emitido al iniciar un nuevo grafo.
   - `SubAgentTaskDelegatedDomainEvent`: Emitido cuando el supervisor delega una subtarea a un agente especialista.
   - `CheckpointSavedDomainEvent`: Emitido tras persistir con éxito un snapshot en base de datos.
   - `WorkflowApprovalRequiredDomainEvent`: Emitido si una acción del subagente requiere revisión humana (gating HITL del Slice 8).
   - `WorkflowCompletedDomainEvent`: Emitido al alcanzar el nodo final con el estado consolidado.
4. **Excepciones de Dominio (`src/domain/agents/exceptions.py`):**
   - `WorkflowNotFoundError`, `InvalidGraphTransitionError`, `GraphCycleDetectedError`, `SubAgentExecutionError`.
5. **Puertos de Dominio (Driven Ports):**
   - `WorkflowCheckpointRepositoryPort`: Contrato para almacenar, recuperar y listar checkpoints de forma transaccional y aislada por inquilino.
   - `AgentCatalogPort`: Contrato para resolver definiciones de agentes, capacidades y políticas asignadas al tenant.

---

### 2.2. Capa de Aplicación (CQRS & State Graph Engine)

1. **Motor de Ejecución de Grafos (`GraphExecutionEngine`):**
   - Servicio orquestador que recorre los nodos del grafo, invoca agentes o transformaciones y evalúa aristas condicionales.
   - Utiliza **AnyIO TaskGroups** (`anyio.create_task_group()`) para bifurcar ejecuciones en paralelo cuando un nodo tiene múltiples transiciones simultáneas o cuando el supervisor delega a varios especialistas a la vez.
2. **Servicio de Reducción de Estados (`StateReducerService`):**
   - Combina de manera determinista los resultados parciales emitidos por subagentes paralelos en el `StateSnapshot` global, resolviendo colisiones mediante estrategias declarativas (ej. mezcla de diccionarios, concatenación de listas de hallazgos o sobreescritura explícita).
3. **Comandos CQRS:**
   - `StartWorkflowCommand` / `StartWorkflowCommandHandler`: Inicializa el grafo, persiste el checkpoint inicial (`version=1`) y despacha la ejecución al nodo de entrada.
   - `ResumeWorkflowCommand` / `ResumeWorkflowCommandHandler`: Recupera el último checkpoint persistido desde MSSQL y reanuda la ejecución exactamente desde el nodo donde se detuvo (ej. tras resolución de una aprobación HITL o recuperación tras fallo).

---

### 2.3. Persistencia de Checkpoints en Microsoft SQL Server 2022

1. **Modelos Físicos SQLModel (`src/infrastructure/persistence/mssql/models.py`):**
   - `WorkflowInstanceModel` (tabla `workflow_instances`):
     - `id`: `NVARCHAR(64)` (Primary Key).
     - `tenant_id`: `NVARCHAR(64)` (Indexado).
     - `name`: `NVARCHAR(255)`.
     - `status`: `NVARCHAR(32)`.
     - `current_node`: `NVARCHAR(128)`.
     - `created_at`, `updated_at`: `DATETIME2`.
   - `WorkflowCheckpointModel` (tabla `workflow_checkpoints`):
     - `id`: `NVARCHAR(64)` (Primary Key).
     - `tenant_id`: `NVARCHAR(64)` (Indexado).
     - `workflow_id`: `NVARCHAR(64)` (Indexado, FK lógica hacia `workflow_instances.id`).
     - `version`: `INT`.
     - `node_id`: `NVARCHAR(128)`.
     - `state_json`: `NVARCHAR(MAX)` (almacena el snapshot completo en formato JSON nativo de SQL Server).
     - `created_at`: `DATETIME2`.
   - Índices compuestos:
     - `(tenant_id, id)` en ambas tablas para garantizar multi-tenancy.
     - `(tenant_id, workflow_id, version DESC)` en `workflow_checkpoints` para obtener el último checkpoint en `O(1)`.
2. **Pessimistic Concurrency Control:**
   - La reanudación y actualización de estado utilizan bloqueo T-SQL pesimista:

     ```sql
     SELECT * FROM workflow_instances WITH (ROWLOCK, UPDLOCK)
     WHERE tenant_id = :tenant_id AND id = :workflow_id;
     ```

   - Esto impide que dos workers o solicitudes HTTP concurrentes intenten reanudar o mutar la misma instancia de workflow al mismo tiempo.
3. **Mapeador DDD (`WorkflowMapper`):**
   - Transforma bidireccionalmente entre entidades de dominio (`WorkflowInstance`, `StateSnapshot`) y modelos SQLModel.
4. **Migración Alembic:**
   - Ubicación física: `src/infrastructure/persistence/mssql/migrations/versions/0006_multi_agent_checkpoints.py`.

---

### 2.4. Mensajería Desacoplada con RabbitMQ y Workers AnyIO

1. **Topología de Agentes (`MultiAgentTopologyConfig`):**
   - Exchange: `ai_platform.agents` (Topic Exchange).
   - Queues especializadas:
     - `agent.supervisor.queue` (routing key: `agent.task.supervisor`)
     - `agent.specialist.queue` (routing key: `agent.task.specialist.#`)
     - `agent.reviewer.queue` (routing key: `agent.task.reviewer`)
     - DLQ: `agent.dead_letter.queue` para aislar mensajes corruptos o reintentos agotados.
2. **Worker Desacoplado (`AnyioSubagentWorker`):**
   - Procesa tareas asignadas a subagentes de forma asíncrona gobernado por `anyio.Semaphore` para control de concurrencia y límites de memoria.

---

### 2.5. Interfaces HTTP y Streaming en Tiempo Real (SSE)

1. **Router de Workflows (`src/interfaces/http/routers/workflows_router.py`):**
   - `POST /tenants/{tenant_id}/workflows`: Inicia un flujo de trabajo (`202 Accepted`).
   - `GET /tenants/{tenant_id}/workflows/{workflow_id}/checkpoints`: Consulta el historial de checkpoints del flujo para inspección y auditoría (`200 OK`).
   - `POST /tenants/{tenant_id}/workflows/{workflow_id}/resume`: Solicita la reanudación de un flujo pausado (`200 OK`).
2. **Notificaciones SSE en Streaming:**
   - Integrado en `src/interfaces/http/api.py` emitiendo eventos estructurados en vivo:
     - `event: agent_handoff`: Datos de delegación entre nodos (`from`, `to`, `step`).
     - `event: subagent_completed`: Notificación de finalización de subtarea con resumen.
     - `event: checkpoint_saved`: Notificación con la versión y nodo asegurados en MSSQL.

---

## 3. Consecuencias y Beneficios

- **Resiliencia Extrema y Reanudabilidad:** Ninguna tarea de larga duración se pierde. Ante caídas de red o reinicios de pods, el grafo se reanuda desde el último snapshot persistido en MSSQL.
- **Concurrencia Segura y Limpia:** El uso de AnyIO TaskGroups garantiza que las excepciones en subagentes paralelos cancelen adecuadamente las tareas vinculadas sin generar corrutinas huérfanas ni fugas de sockets.
- **Time-Travel Debugging y Auditoría:** Los operadores pueden reconstruir y auditar la secuencia exacta de decisiones de cada subagente en cada versión del checkpoint.
- **Sinergia Total con el Ecosistema:** Aprovecha las cuotas de tokens del Slice 6, las citas y documentos del Slice 7, y las barreras HITL del Slice 8.
- **Velocidad de Testing TDD:** Contratos abstractos y el adaptador `InMemoryWorkflowCheckpointRepositoryAdapter` permiten validar la lógica de grafos y transiciones complejas en milisegundos sin requerir servicios externos levantados.
