# ADR 0007: Invocación Segura de Herramientas (Tool Calling), Entornos Aislados (Sandbox) y Aprobación Humana (HITL)

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-28
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 8 — Secure Tool Calling, Sandboxed Execution & Human-in-the-Loop (HITL)

---

## 1. Contexto y Problemática

Con la consolidación de la búsqueda semántica e ingesta de conocimiento (Slice 7), la plataforma evoluciona de un sistema conversacional puramente consultivo hacia un **motor de agentes autónomos capaces de interactuar con sistemas externos y ejecutar acciones**.

Esta transición introduce desafíos de seguridad, confiabilidad y gobernanza crítica:

1. **Riesgo de Ejecución Destructiva o No Autorizada (Side Effects):**
   - Los modelos de lenguaje (LLMs) son probabilísticos y propensos a alucinaciones o interpretaciones erróneas.
   - Una herramienta que muta datos o tiene impacto financiero/operativo (ej. *"reembolsar $150 al pedido #4912"*, *"bloquear usuario"*, *"borrar registro de base de datos"*) **jamás debe ejecutarse automáticamente a ciegas** sin supervisión.
2. **Human-in-the-Loop (HITL) y Bloqueo Concurrente:**
   - Se requiere un mecanismo formal de retención que suspenda el flujo de la conversación en estado `WAITING_APPROVAL` hasta que un operador humano facultado apruebe o rechace la acción.
   - En entornos multi-operador, se debe prevenir condiciones de carrera: dos administradores concurrentes no deben poder autorizar o rechazar la misma acción simultáneamente (doble ejecución).
3. **Ejecución Aislada, Resiliente y con Límites Temporales (Sandboxed Runner):**
   - Las herramientas externas (APIs HTTP, webhooks, microservicios de terceros) pueden sufrir degradación, demoras excesivas o devolver payloads corruptos.
   - Es mandatorio aislar la ejecución bajo primitivas de concurrencia estructurada (**AnyIO**), gobernadas por límites de tiempo estrictos (`anyio.fail_after`), semáforos de concurrencia y captura defensiva de excepciones para evitar el colapso del worker o del servidor HTTP.
4. **Trazabilidad y Auditoría Transaccional en Microsoft SQL Server 2022:**
   - Toda solicitud de herramienta, parámetros exactos evaluados contra JSON Schema, decisión del operador (con justificación/identificador) y salida del sandbox deben registrarse de forma inmutable en **MSSQL 2022**, con estricto aislamiento por `tenant_id`.

---

## 2. Decisión de Diseño

Se adopta una solución integral basada en Clean Architecture, DDD, CQRS, AnyIO y persistencia transaccional en Microsoft SQL Server:

### 2.1. Modelo de Dominio de Herramientas y Aprobaciones (DDD)

1. **Value Objects (`src/domain/tools/value_objects/`):**
   - `ToolDefinition`: Define formalmente una herramienta disponible: nombre (`tool_name`), descripción, esquema JSON de parámetros derivado de Pydantic v2 (`parameters_schema: dict`), indicador de determinismo (`is_deterministic: bool`) y si requiere autorización previa (`requires_approval: bool`).
   - `ToolCall`: Representa la intención emitida por el LLM: identificador único (`call_id`), nombre de la herramienta, diccionario validado de argumentos (`arguments: dict`) y timestamp de creación.
   - `ToolResult`: Representa la salida de la ejecución en sandbox: `call_id`, contenido serializado de la respuesta (`output: str`), bandera de error (`is_error: bool`) y latencia en milisegundos (`execution_time_ms: float`).
2. **Entidad / Agregado de Aprobación (`ToolApprovalRequest`):**
   - Agregado que administra el ciclo de vida de una solicitud de aprobación humana:
     - Estados: `PENDING` ➔ `APPROVED` | `REJECTED` | `EXPIRED`.
     - Invariantes: Solo una solicitud en estado `PENDING` puede ser aprobada o rechazada. La aprobación requiere `operator_id` y `justification` opcional.
     - Emite eventos de dominio: `ToolApprovalRequiredDomainEvent`, `ToolApprovalResolvedDomainEvent`.
3. **Eventos de Dominio (`src/domain/tools/events/`):**
   - `ToolCallRequestedDomainEvent`: Notifica que el LLM ha solicitado invocar una herramienta.
   - `ToolApprovalRequiredDomainEvent`: Notifica la retención de la conversación pendiente de revisión humana.
   - `ToolExecutionCompletedDomainEvent`: Notifica que la herramienta finalizó en el sandbox con su resultado.
4. **Puertos de Dominio (Driven Ports):**
   - `ToolRegistryPort`: Contrato para consultar y verificar herramientas autorizadas y habilitadas por tenant.
   - `ToolApprovalRepositoryPort`: Contrato de persistencia para guardar, consultar y resolver solicitudes de aprobación.
   - `SandboxedToolRunnerPort`: Contrato abstracto para la ejecución aislada de herramientas (`execute(tool_call: ToolCall, timeout_seconds: float) -> ToolResult`).

---

### 2.2. Capa de Aplicación (CQRS & Políticas de Ejecución)

1. **Servicio Evaluador de Políticas (`ToolPolicyEvaluatorService`):**
   - Inspecciona la llamada de la herramienta contra la definición en el `ToolRegistryPort` y las directivas del inquilino (`TenantPolicy`).
   - Si `requires_approval=True` o el inquilino opera bajo modo estricto, genera una `ToolApprovalRequest` en estado `PENDING` y suspende la conversación.
   - Si `requires_approval=False`, despacha directamente la ejecución hacia el sandbox.
2. **Comandos CQRS:**
   - `ApproveToolExecutionCommand` / `ApproveToolExecutionCommandHandler`: Registra la decisión positiva del operador y encola el trabajo de ejecución en RabbitMQ.
   - `RejectToolExecutionCommand` / `RejectToolExecutionCommandHandler`: Registra el rechazo formal, liberando la conversación con un mensaje explicativo para el usuario.
   - `ExecuteSandboxedToolCommand` / `ExecuteSandboxedToolCommandHandler`: Ejecuta la herramienta de forma aislada a través de `SandboxedToolRunnerPort` y almacena la auditoría.

---

### 2.3. Infraestructura MSSQL 2022 y Control de Concurrencia Pesimista

1. **Modelos Físicos SQLModel (`src/infrastructure/persistence/mssql/models.py`):**
   - `ToolApprovalModel` (tabla `tool_approvals`): `id`, `tenant_id` (indexado), `conversation_id`, `tool_name`, `arguments_json`, `status`, `operator_id`, `justification`, `created_at`, `resolved_at`.
   - `ToolExecutionAuditModel` (tabla `tool_execution_audits`): `id`, `tenant_id` (indexado), `call_id`, `tool_name`, `arguments_json`, `output_json`, `is_error`, `execution_time_ms`, `created_at`.
   - Índices compuestos: `(tenant_id, id)` y `(tenant_id, status)`.
2. **Pessimistic Row-Level Locking:**
   - Para evitar que múltiples operadores aprueben o rechacen la misma acción simultáneamente, `MssqlToolApprovalRepository` utiliza bloqueo T-SQL pesimista:

     ```sql
     SELECT * FROM tool_approvals WITH (ROWLOCK, UPDLOCK)
     WHERE tenant_id = :tenant_id AND id = :approval_id AND status = 'PENDING';
     ```

3. **Ejecución en Sandbox con AnyIO:**
   - `AnyioSandboxedToolRunnerAdapter` ejecuta la herramienta dentro de `anyio.fail_after(timeout_seconds)`.
   - En caso de `TimeoutError`, cancela la tarea limpiamente y retorna un `ToolResult(is_error=True, output="Tool execution timed out")` sin fugas de recursos ni hilos huérfanos.

---

### 2.4. Mensajería Desacoplada con RabbitMQ

1. **Topología de Herramientas (`ToolsTopologyConfig`):**
   - Exchange: `ai_platform.tools` (Topic Exchange).
   - Queue: `tools.execution.queue` para despachar llamadas autorizadas hacia workers de background.
   - DLQ: `tools.execution.dlq` para aislar herramientas fallidas irrecuperables.
2. **Worker Asíncrono (`AnyioToolExecutionWorker`):**
   - Consume mensajes de ejecución de herramientas, delega al sandbox y emite el evento de resultado de vuelta a la conversación para que el worker de LLM sintetice la respuesta final.

---

### 2.5. Interfaces HTTP y Notificaciones SSE en Streaming

1. **Endpoints Administrativos de Aprobaciones (`/tenants/{tenant_id}/approvals`):**
   - `GET /tenants/{tenant_id}/approvals/pending`: Lista acciones retenidas para el tenant.
   - `POST /tenants/{tenant_id}/approvals/{approval_id}/decision`: Envía la decisión (`APPROVED` o `REJECTED`) con firma de operador.
2. **Eventos Server-Sent Events (SSE):**
   - `event: tool_call_started`: Informa al cliente que el asistente está consultando una herramienta.
   - `event: tool_approval_required`: Informa en tiempo real que la acción requiere confirmación de un supervisor.

---

## 3. Consecuencias y Beneficios

- **Seguridad Infranqueable:** Ninguna acción crítica se ejecuta sin la firma y registro de un operador humano en MSSQL.
- **Resiliencia Operativa:** Las fallas de APIs externas o timeouts quedan encapsuladas en `ToolResult` sin abortar el worker ni tumbar el hilo principal.
- **Transparencia y Trazabilidad:** Historial de auditoría inmutable de todas las herramientas ejecutadas para auditorías de cumplimiento (SOC2 / ISO 27001).
- **Desarrollo TDD Limpio:** Los contratos abstractos y adaptadores en memoria permiten simular todo el flujo HITL en menos de 2 segundos en tests unitarios.
