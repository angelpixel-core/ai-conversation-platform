# ADR 0016: Estandarización de la Capa de Infraestructura, Nomenclatura de Adaptadores, Mappers Bidireccionales y Resiliencia de Conexiones

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `refactor/source-code-and-clean-arch-polish` — Sección 2.3 y Paso 3 de RFC 02

---

## 1. Contexto y Problemática

En la arquitectura Clean / Hexagonal (Ports & Adapters) de `ai-conversation-platform`, la **Capa de Infraestructura (`src/infrastructure/`)** implementa los puertos conducidos (**Driven Ports**) definidos por el dominio y la aplicación, tales como persistencia relacional en MSSQL, colas y tópicos en RabbitMQ, clientes HTTP/LLM, escáneres de seguridad y corredores de herramientas.

Durante la revisión integral de código (RFC 02), se identificaron las siguientes oportunidades de mejora:

1. **Heterogeneidad en la Nomenclatura de Adaptadores:**
   - Ciertas clases de adaptadores poseían nombres descriptivos directos sin el sufijo de patrón (ej. `MssqlConversationRepository`, `InMemoryUnitOfWork`, `HttpxClient`, `AnyioSandboxedToolRunner`), mientras que otras ya utilizaban el sufijo canónico (ej. `InMemoryTenantRepositoryAdapter`, `RegexPiiScannerAdapter`, `RabbitMQPublisherAdapter`).
2. **Asimetría en las Firmas de Data Mappers:**
   - La persistencia relacional utiliza SQLModel/SQLAlchemy para definir tablas físicas (`*Model`). Los mappers bidireccionales (`*Mapper` / `*DataMapper`) traducían a modelos con nombres inconsistentes (`to_model()`, `to_entity()`, `to_model_document()`, etc.) en lugar de una interfaz uniforme con métodos canónicos estáticos `to_domain()` y `to_persistence()`.
3. **Resiliencia de Conexiones e I/O Transitorio:**
   - Se requería estandarizar y explicitar los parámetros de timeouts por defecto, pooling con pre-ping, reconexión automática en RabbitMQ y resiliencia ante cortes transitorios de red para garantizar alta disponibilidad en entornos productivos.

---

## 2. Decisión de Diseño

Se aprueba y ejecuta la estandarización canónica de la Capa de Infraestructura conforme a los siguientes lineamientos:

### 2.1. Nomenclatura Uniforme de Adaptadores (`<Technology><Port>Adapter`)

Todos los adaptadores de infraestructura adoptan la nomenclatura canónica `<Technology><Port>Adapter`, garantizando el 100% de retrocompatibilidad mediante alias directos:

#### A. Persistencia Relacional MSSQL (`src/infrastructure/persistence/mssql/`):
- `MssqlConversationRepositoryAdapter = MssqlConversationRepository` (implementa `ConversationRepositoryPort`)
- `MssqlTenantRepositoryAdapter = MssqlTenantRepository` (implementa `TenantRepositoryPort`)
- `MssqlIncidentRepositoryAdapter = MssqlIncidentRepository` (implementa `IncidentRepositoryPort`)
- `MssqlKnowledgeRepositoryAdapter = MssqlKnowledgeRepository` (implementa `KnowledgeRepositoryPort`)
- `MssqlToolApprovalRepositoryAdapter = MssqlToolApprovalRepository` (implementa `ToolApprovalRepositoryPort`)
- `MssqlWorkflowCheckpointRepositoryAdapter = MssqlWorkflowCheckpointRepository` (implementa `WorkflowCheckpointRepositoryPort`)
- `MssqlAuditRepositoryAdapter = MssqlAuditRepository` (implementa `AuditRepositoryPort`)
- `MssqlIdempotencyRepositoryAdapter = MssqlIdempotencyRepository` (implementa `IdempotencyRepositoryPort`)
- `MssqlOutboxRepositoryAdapter = MssqlOutboxRepository`
- `MssqlStreamBufferRepositoryAdapter = MssqlStreamBufferRepository` (implementa `StreamBufferRepositoryPort`)
- `MssqlUnitOfWorkAdapter = MssqlUnitOfWork` (implementa `UnitOfWorkPort`)

#### B. Persistencia In-Memory (`src/infrastructure/persistence/in_memory/`):
- `InMemoryConversationRepositoryAdapter = InMemoryConversationRepository`
- `InMemoryTenantRepository = InMemoryTenantRepositoryAdapter`
- `InMemoryIncidentRepository = InMemoryIncidentRepositoryAdapter`
- `InMemoryKnowledgeRepository = InMemoryKnowledgeRepositoryAdapter`
- `InMemoryToolApprovalRepositoryAdapter = InMemoryToolApprovalRepository`
- `InMemoryAuditRepository = InMemoryAuditRepositoryAdapter`
- `InMemoryIdempotencyRepository = InMemoryIdempotencyRepositoryAdapter`
- `InMemoryStreamBufferRepository = InMemoryStreamBufferRepositoryAdapter`
- `InMemoryUnitOfWorkAdapter = InMemoryUnitOfWork`
- `InMemoryOutboxRepositoryAdapter = InMemoryOutboxRepository`
- `InMemoryMessageBrokerAdapter = InMemoryMessageBroker`

#### C. Mensajería, Seguridad y Herramientas:
- `RabbitMqPublisherAdapter = RabbitMQPublisherAdapter` / `RabbitMqEventPublisherAdapter = RabbitMQPublisherAdapter`
- `RabbitMqConsumerAdapter = RabbitMQConsumerAdapter` / `RabbitMqEventConsumerAdapter = RabbitMQConsumerAdapter`
- `HttpxHttpClientAdapter = HttpxClient` / `HttpxClientAdapter = HttpxClient`
- `AnyioSandboxedToolRunnerAdapter = AnyioSandboxedToolRunner`
- `AnyioStreamGuardrailFilterAdapter = AnyioStreamGuardrailFilter`
- `RegexPiiScannerAdapter` (mantenido canónico)
- `HeuristicInjectionDetectorAdapter` (mantenido canónico)

---

### 2.2. Convención Canónica de Mappers Bidireccionales (`to_domain` y `to_persistence`)

Se establece que todo mapper de persistencia exponga de forma obligatoria los métodos estáticos:
- `to_domain(model)`: Transforma el modelo ORM/SQLModel en la entidad o agregado del dominio.
- `to_persistence(entity)`: Transforma la entidad o agregado del dominio en el modelo SQLModel persistible.

Mappers actualizados:
1. `ConversationDataMapper` / `ConversationMapper` (`src/infrastructure/persistence/mssql/mapper.py`):
   - `to_domain(model: ConversationModel) -> Conversation`
   - `to_persistence(entity: Conversation) -> ConversationModel` (alias a `to_model`)
2. `TenantDataMapper` / `TenantMapper` (`src/infrastructure/persistence/mssql/tenant_mapper.py`):
   - `to_domain(model: TenantModel) -> Tenant`
   - `to_persistence(entity: Tenant) -> TenantModel` (alias a `to_model`)
3. `KnowledgeDataMapper` / `KnowledgeMapper` (`src/infrastructure/persistence/mssql/knowledge_mapper.py`):
   - `to_domain(model: DocumentModel) -> Document`
   - `to_persistence(domain: Document) -> DocumentModel`
   - `to_domain_chunk(model: DocumentChunkModel) -> DocumentChunk`
   - `to_persistence_chunk(domain: DocumentChunk) -> DocumentChunkModel`
4. `ToolApprovalMapper` / `ToolApprovalDataMapper` (`src/infrastructure/persistence/mssql/tool_approval_mapper.py`):
   - `to_domain(model: ToolApprovalModel) -> ToolApprovalRequest` (alias a `to_entity`)
   - `to_persistence(entity: ToolApprovalRequest) -> ToolApprovalModel` (alias a `to_model`)
5. `WorkflowMapper` / `WorkflowDataMapper` (`src/infrastructure/persistence/mssql/workflow_mapper.py`):
   - `to_domain(model: WorkflowInstanceModel) -> WorkflowInstance` (alias a `to_domain_instance`)
   - `to_persistence(domain: WorkflowInstance) -> WorkflowInstanceModel` (alias a `to_model_instance`)
   - `to_domain_checkpoint(model: WorkflowCheckpointModel) -> StateSnapshot`
   - `to_persistence_checkpoint(domain: StateSnapshot) -> WorkflowCheckpointModel`
6. `GovernanceMapper` / `GovernanceDataMapper` (`src/infrastructure/persistence/mssql/governance_mapper.py`):
   - `to_domain(model: SecurityIncidentModel) -> SecurityIncident`
   - `to_persistence(domain: SecurityIncident) -> SecurityIncidentModel` (alias a `to_model`)

---

### 2.3. Matriz de Resiliencia de Conexiones e I/O

Se consolidan las siguientes garantías de resiliencia en la capa de infraestructura:

| Componente | Mecanismo de Resiliencia | Configuración / Parámetros |
| :--- | :--- | :--- |
| **MSSQL (SQLModel / SQLAlchemy)** | Connection Pool con healthcheck preventivo y timeouts de conexión | `pool_pre_ping=True`, `pool_recycle=1800`, `login_timeout=5`, `timeout=15`, reintentos en test fixture `clean_db`. |
| **RabbitMQ (aio-pika)** | Reconexión automática con robust connection y backoff progresivo | `connect_robust`, 15 intentos de conexión con retardo de 2.0s antes de fallar. |
| **HTTP Clients (HTTPX)** | Timeouts granulares obligatorios por cliente y por petición | `default_timeout=30.0` configurable en constructor, headers y stream context managers cerrados en bloque `finally`. |
| **Tools Sandbox (AnyIO)** | Aislamiento temporal con timeouts duros cancelables | `anyio.fail_after(timeout_seconds=10.0)` capturando `TimeoutError` sin bloquear event loop. |
| **Transactional Outbox** | Commit atómico de lote y marcas de falla con retries automáticos | Rollback seguro en bloque `try/except` con logs estructurados ante TDS lock drops. |

---

## 3. Consecuencias y Beneficios

1. **Aislamiento Total del Dominio:** Las entidades de dominio nunca interactúan con SQLModel ni conocen la estructura relacional de las tablas. La persistencia ocurre a través de mappers puros.
2. **Claridad Arquitectónica:** Todos los componentes de infraestructura comunican claramente su rol (`*Adapter`, `*Mapper`, `*Model`) sin ambigüedad.
3. **Cero Regresiones (Zero Breaking Changes):** Todos los símbolos preexistentes se mantienen como alias exportados en sus respectivos submódulos y paquetes `__init__.py`.
4. **Verificación Automatizada:** Cobertura de pruebas unitarias al 100% en `tests/unit/infrastructure/test_adapter_and_mapper_conformance.py` validando tipado, métodos estáticos y compatibilidad de subclases.
