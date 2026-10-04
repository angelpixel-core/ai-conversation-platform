# ADR 0015: Estandarización de la Capa de Aplicación, Protocolos CQRS, Driven Ports y UnitOfWork

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `refactor/source-code-and-clean-arch-polish` — Sección 2.2 y Paso 2 de RFC 02

---

## 1. Contexto y Problemática

En la arquitectura Clean / Hexagonal del proyecto `ai-conversation-platform`, la **Capa de Aplicación (`src/application/`)** coordina los casos de uso del sistema mediando entre los adaptadores de entrada (routers HTTP, workers AMQP) y el modelo de dominio (`src/domain/`), apoyándose en puertos de infraestructura (**Driven Ports**).

Tras la implementación de los 10 Slices del Roadmap, se identificaron asimetrías de diseño en esta capa:

1. **Inconsistencias en Nomenclatura CQRS:**
   - Algunos casos de uso utilizaban la nomenclatura `<Action>Handler` (ej. `CreateConversationHandler`, `UploadDocumentHandler`, `ApproveToolExecutionHandler`), mientras que otros utilizaban `<Action>CommandHandler` (ej. `ProvisionTenantCommandHandler`, `StartWorkflowCommandHandler`).
2. **Puertos de Infraestructura (Driven Ports) sin Sufijo Canónico:**
   - Contratos clave como [EventPublisher](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/application/shared/ports/event_publisher.py), [HttpClient](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/application/shared/ports/http_client.py), [UnitOfWork](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/application/shared/ports/unit_of_work.py) y [ConversationRepository](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/conversations/ports/conversation_repository.py) no poseían el sufijo canónico `Port`, a diferencia de `IncidentRepositoryPort`, `TenantRepositoryPort`, `IdempotencyRepositoryPort`, etc.
3. **Uso de Excepciones Genéricas en Handlers:**
   - Varios handlers capturaban o lanzaban `ValueError` genérico (ej. `raise ValueError("Tenant no encontrado")`) en lugar de aprovechar las excepciones semánticas de dominio formalizadas en [ADR 0014](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/.agent/architecture/decisions/0014-domain-layer-standardization-and-clean-arch-polish.md).
4. **Ausencia de Protocolos Base para Handlers y Excepciones de Aplicación:**
   - No existían protocolos estándar en Python (`typing.Protocol`) que definieran el contrato estructural de ejecución para comandos y queries, ni una jerarquía formal para errores propios de la capa de aplicación (`ApplicationError`).

---

## 2. Decisión de Diseño

Se aprueba y ejecuta la estandarización canónica de la Capa de Aplicación conforme a los siguientes lineamientos:

### 2.1. Protocolos Genéricos CQRS (`src/application/shared/cqrs/base.py`)

Se crean protocolos tipados para desacoplar y formalizar el contrato de los handlers:

```python
class CommandHandler(Protocol[TCommand, TResult]):
    def handle(self, command: TCommand, *args: Any, **kwargs: Any) -> TResult: ...

class AsyncCommandHandler(Protocol[TCommand, TResult]):
    async def handle(self, command: TCommand, *args: Any, **kwargs: Any) -> TResult: ...

class QueryHandler(Protocol[TQuery, TResult]):
    def handle(self, query: TQuery, *args: Any, **kwargs: Any) -> TResult: ...

class AsyncQueryHandler(Protocol[TQuery, TResult]):
    async def handle(self, query: TQuery, *args: Any, **kwargs: Any) -> TResult: ...
```

### 2.2. Jerarquía de Excepciones de Aplicación (`src/application/shared/exceptions.py`)

Se establece una raíz unificada para errores del ciclo de orquestación de casos de uso:

- `ApplicationError(Exception)`: Clase base con soporte para `message` y `details: dict[str, object]`.
- `ApplicationValidationError(ApplicationError, ValueError)`: Violaciones de validación a nivel de caso de uso.
- `IdempotencyConflictError(ApplicationError)`: Conflicto de concurrencia o bloqueo de idempotencia en progreso.
- `TenantAccessDeniedError(ApplicationError, PermissionError)`: Intentos de acceso inter-inquilino no autorizados.

### 2.3. Homogeneización de Nombres de Handlers y Retrocompatibilidad

Todos los handlers se unifican bajo la convención:
- **Commands:** `<Action>Command` y `<Action>CommandHandler` (método `handle(command: <Action>Command) -> <ResultDTO>`).
- **Queries:** `<Entity>Query` y `<Entity>QueryHandler` (método `handle(query: <Entity>Query) -> <ResultDTO>`).

Para evitar regresiones en routers HTTP, scripts de wiring (`container.py`, `main.py`) o pruebas existentes, se declaran alias explícitos en cada módulo:
- `CreateConversationHandler = CreateConversationCommandHandler`
- `SendMessageHandler = SendMessageCommandHandler`
- `AppendAssistantMessageHandler = AppendAssistantMessageCommandHandler`
- `UploadDocumentHandler = UploadDocumentCommandHandler`
- `IndexDocumentChunksHandler = IndexDocumentChunksCommandHandler`
- `ProvisionTenantHandler = ProvisionTenantCommandHandler`
- `ReserveQuotaHandler = ReserveQuotaCommandHandler`
- `SettleQuotaHandler = SettleQuotaCommandHandler`
- `ApproveToolExecutionHandler = ApproveToolExecutionCommandHandler`
- `RejectToolExecutionHandler = RejectToolExecutionCommandHandler`
- `ExecuteSandboxedToolHandler = ExecuteSandboxedToolCommandHandler`
- `RecordSecurityIncidentHandler = RecordSecurityIncidentCommandHandler`
- `StartWorkflowHandler = StartWorkflowCommandHandler`
- `ResumeWorkflowHandler = ResumeWorkflowCommandHandler`
- `StreamConversationHandler = StreamConversationQueryHandler`
- `ResumeStreamHandler = ResumeStreamQueryHandler`
- `GetGovernanceMetricsHandler = GetGovernanceMetricsQueryHandler`
- `ListIncidentsHandler = ListIncidentsQueryHandler`

### 2.4. Estandarización de Puertos (Driven Ports)

Se define la clase canónica con sufijo `*Port` y se mantiene el alias previo para retrocompatibilidad:

| Archivo del Puerto | Clase Canónica | Alias de Compatibilidad |
| :--- | :--- | :--- |
| `src/application/shared/ports/event_publisher.py` | `EventPublisherPort` | `EventPublisher = EventPublisherPort` |
| `src/application/shared/ports/http_client.py` | `HttpClientPort` | `HttpClient = HttpClientPort` |
| `src/application/shared/ports/unit_of_work.py` | `UnitOfWorkPort` | `UnitOfWork = UnitOfWorkPort` |
| `src/domain/conversations/ports/conversation_repository.py` | `ConversationRepository` | `ConversationRepositoryPort = ConversationRepository` |

### 2.5. Integración de Excepciones Semánticas de Dominio en Handlers

Se reemplazaron las ocurrencias de `raise ValueError(...)` en handlers por excepciones semánticas con herencia dual (`DomainError, ValueError`):
- `TenantAlreadyExistsError`: En `ProvisionTenantCommandHandler` cuando el slug de tenant ya está registrado.
- `TenantNotFoundError`: En `ReserveQuotaCommandHandler`, `SettleQuotaCommandHandler` y `UploadDocumentCommandHandler`.
- `DocumentValidationError`: En `IndexDocumentChunksCommandHandler` cuando el lote de fragmentos está vacío.
- `ToolApprovalNotFoundError`: En `ApproveToolExecutionCommandHandler` y `RejectToolExecutionCommandHandler`.
- `ToolNotAllowedError`: En `ExecuteSandboxedToolCommandHandler` si la herramienta no está permitida por política.
- `WorkflowNotFoundError` y `WorkflowStateError`: En `ResumeWorkflowCommandHandler` para instancias inexistentes o estados no reanudables.

---

## 3. Consecuencias y Beneficios

### Positivas:
- **Consistencia Arquitectónica:** Cumplimiento total de la regla DDD/CQRS en la que cada caso de uso expone una intención clara y predecible.
- **Tipado Fuerte y Estático:** Los handlers pueden tiparse genéricamente con `CommandHandler[C, R]` y `QueryHandler[Q, R]`.
- **Cero Regresiones (Zero Breaking Changes):** Gracias a los alias y al patrón dual-inheritance de las excepciones, ningún router, test o worker existente requirió cambios destructivos.
- **Contratos Claros de Unit of Work:** `UnitOfWorkPort` documenta y tipa explícitamente el límite transaccional atómico y el dispatch de outbox.

### Negativas / Deuda Técnica Mitigada:
- Existencia temporal de alias que facilitan la transición; en fases futuras de major release podrán ser deprecados ordenadamente.

---

## 4. Estado de Validación

- **Suite de Pruebas:** 637 tests pasando (incluyendo `test_cqrs_handler_conformance.py` con 5 tests nuevos).
- **Linters y Type Checking:** 0 advertencias en Ruff, 0 errores en Pyright, 0 vulnerabilidades en Bandit.
