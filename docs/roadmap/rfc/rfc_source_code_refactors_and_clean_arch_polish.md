# RFC 02 — Refactor y Estandarización de Código Fuente (Clean Architecture, DDD, Tipado Estricto y Convenciones)

- **Estado:** Propuesto / En Revisión
- **Rama Asociada (Futura):** `refactor/source-code-and-clean-arch-polish`
- **Ámbitos:** Dominio, Aplicación, Infraestructura, Interfaces HTTP, Pyright, Ruff, Testing Suite
- **Fecha:** Octubre 2026

---

## 1. Contexto y Diagnóstico

Tras la culminación exitosa de los 10 Slices del Roadmap, la base de código de `ai-conversation-platform` cuenta con:

- Más de **11.750 líneas de código Python**.
- **445 archivos** fuente y de tests.
- **611 pruebas automatizadas** pasando al 100%.

Durante la fase de aceleración de características (features), algunas convenciones de nomenclatura, formatos de docstrings, estructuras de imports y patrones de manejo de errores evolucionaron con pequeñas diferencias estilísticas entre los primeros slices (Slices 1–4) y los slices más avanzados (Slices 8–10).

El objetivo de este RFC es definir el estándar canónico definitivo para el código fuente, preparando una refactorización integral, limpia y segura que preserve al 100% las invariantes de negocio y garantice mantenibilidad de nivel empresarial.

---

## 2. Convenciones por Capas Arquitectónicas

Siguiendo las directivas de `.agent/rules/00-core-philosophy.md`:

```
               [ Interfaces ]  (FastAPI Routers, CLI, Middlewares)
                     │
                     ▼
              [ Application ]  (CQRS Handlers, Ports, UoW)
                     │
                     ▼
                 [ Domain ]    (Entities, Value Objects, Domain Events)
                     ▲
                     │
             [ Infrastructure ] (MSSQL, RabbitMQ, LLM Adapters, OpenTelemetry)
```

### 2.1. Capa de Dominio (`src/domain/`) — [Completado / ADR 0014]

- [x] **Regla Inquebrantable:** Cero dependencias de librerías externas o frameworks (FastAPI, SQLModel, SQLAlchemy, Pydantic no-puro, AnyIO).
- [x] **Value Objects:**
  - Deben ser inmutables utilizando `@dataclass(frozen=True)` o clases inmutables con validación estricta en `__post_init__`.
  - Deben proveer métodos factoría semánticos (`create()`, `from_raw()`, etc.) y métodos de comparación por valor.
  - Deduplicación consolidada (ej. `CheckpointId` unificado en `checkpoint_id.py`).
- [x] **Entidades y Agregados (Aggregate Roots):**
  - Identificador único tipado (ej. `TenantId`, `ConversationId`).
  - Estado encapsulado: atributos privados protegidos (`_id`, `_status`, `_balance`, `_messages`) con propiedades públicas de solo lectura.
  - Mutación exclusiva a través de métodos de negocio que validen invariantes y emitan Domain Events (`record_event(...)`).
- [x] **Domain Events:**
  - Nomenclatura en pasado imperativo: `<Aggregate><Action>DomainEvent` (ej. `SafetyViolationBlockedDomainEvent`, `MessageAppendedDomainEvent`).
  - Carga útil (`payload`) inmutable y serializable.
- [x] **Excepciones de Dominio:**
  - Jerarquía unificada en `src/domain/shared/exceptions.py` (`DomainError`, `DomainException`, `DomainValidationError`, `EntityNotFoundError`, `InvariantViolationError`).
  - Dual-inheritance (`DomainError, ValueError`) para garantizar retrocompatibilidad total sin romper tests ni handlers existentes.
  - Formalizado en [ADR 0014](../../../.agent/architecture/decisions/0014-domain-layer-standardization-and-clean-arch-polish.md).

### 2.2. Capa de Aplicación (`src/application/`) — [Completado / ADR 0015]

- [x] **Separación CQRS:**
  - **Commands:** Mutan estado, retornan DTOs de resultado o `None`. Nomenclatura: `<Action>Command` y `<Action>CommandHandler`.
  - **Queries:** Solo lectura, no generan efectos secundarios. Nomenclatura: `<Entity>Query` y `<Entity>QueryHandler`.
  - **Protocolos Genéricos:** `CommandHandler[C, R]`, `AsyncCommandHandler[C, R]`, `QueryHandler[Q, R]`, `AsyncQueryHandler[Q, R]` en `src/application/shared/cqrs/base.py`.
  - **Retrocompatibilidad Total:** Alias para todos los handlers previos (ej. `CreateConversationHandler = CreateConversationCommandHandler`).
- [x] **Puertos (Driven Ports):**
  - Interfaces abstractas puras utilizando `typing.Protocol` o `abc.ABC`.
  - Nomenclatura uniforme con sufijo `*Port`: `EventPublisherPort`, `HttpClientPort`, `UnitOfWorkPort`, `ConversationRepositoryPort`.
- [x] **Unit of Work (UoW):**
  - Context manager explícito (`with unit_of_work as uow:`) que agrupa repositorios bajo una misma transacción y confirma con `uow.commit()`.
  - Tipado y contratos abstractos reforzados en `UnitOfWorkPort`.
- [x] **Excepciones de Aplicación:**
  - Raíz `ApplicationError(Exception)` en `src/application/shared/exceptions.py`.
  - Adopción exhaustiva de excepciones semánticas de dominio (con herencia dual) en todos los handlers de negocio.
- [x] **Formalización:** Documentado en [ADR 0015](../../../.agent/architecture/decisions/0015-application-layer-standardization-and-cqrs-polish.md).

### 2.3. Capa de Infraestructura (`src/infrastructure/`) — [Completado / ADR 0016]

- [x] **Adaptadores:**
  - Nomenclatura explícita y canónica: `<Technology><Port>Adapter` (ej. `MssqlIncidentRepositoryAdapter`, `MssqlConversationRepositoryAdapter`, `RabbitMqEventPublisherAdapter`, `HttpxHttpClientAdapter`, `InMemoryUnitOfWorkAdapter`).
  - Retrocompatibilidad absoluta: exportación de alias de clase para 100% de componentes previos.
- [x] **Persistencia y Modelos ORM:**
  - Separación rigurosa entre modelos de base de datos (`*Model` en SQLModel/SQLAlchemy) y entidades de dominio.
  - Mappers dedicados (`*Mapper` / `*DataMapper`) con métodos canónicos estáticos `to_domain()` y `to_persistence()`.
- [x] **Resiliencia de Conexiones:**
  - Políticas de timeout por defecto (30s HTTPX, 15s MSSQL login/query, 10s tool runner).
  - Reconexión robusta con exponential backoff en RabbitMQ (`aio_pika.connect_robust`).
  - Pre-ping y connection pooling en MSSQL (`pool_pre_ping=True`, `pool_recycle=1800`).
- [x] **Formalización:** Documentado en [ADR 0016](../../../.agent/architecture/decisions/0016-infrastructure-layer-standardization-and-adapters-polish.md).

### 2.4. Capa de Interfaces (`src/interfaces/`) — [Completado / ADR 0017]

- [x] **Controladores y Routers:**
  - Nomenclatura uniforme `<entity>_router.py` en `src/interfaces/http/routers/` (ej. `conversations_router.py`, `approvals_router.py`, `governance_router.py`, `knowledge_router.py`, `tenant_admin_router.py`, `workflows_router.py`).
  - Extracción de la lógica de transporte de conversaciones, mensajes y SSE streaming desde `api.py` a `conversations_router.py`.
  - Los endpoints HTTP delegan inmediatamente en Application Handlers o Servicios coordinadores; prohibido escribir lógica de negocio en routers.
- [x] **DTOs y Esquemas (Pydantic v2):**
  - Distinción entre Requests (`*Request`) y Responses (`*Response`).
  - Decoradores y validaciones con `Field(...)`, `minLength`, `maxLength`, `description` y `examples`.
  - Aliases canónicos para retrocompatibilidad total (`CitationResponse = CitationSchema`, `AgentActivityEventResponse = AgentActivityEventSchema`).
- [x] **Estandarización de Errores HTTP con RFC 7807 (Problem Details):**
  - Modelo `ProblemDetails` y fábrica `problem_details_response` en `src/interfaces/http/problem_details.py`.
  - Tipo de contenido `application/problem+json` y exception handlers globales en `api.py`.
  - Retrocompatibilidad absoluta: preservación de extensiones legadas (`error`, `message`, `violation_type`, `incident_id`, etc.) sin romper tests existentes.
- [x] **Formalización:** Documentado en [ADR 0017](../../../.agent/architecture/decisions/0017-interfaces-layer-standardization-and-problem-details.md).


---

## 3. Estándar de Tipado Estricto y Docstrings — [Completado / ADR 0018]

### 3.1. Tipado Estático (Python 3.12+ / Pyright)

- [x] **Uniones Modernas:** Utilizar siempre el operador `|` en lugar de `Union[A, B]` u `Optional[A]`. Erradicados todos los tipos legados de `typing` en código productivo de `src/`.
- [x] **Colecciones Built-in:** Utilizar `list[T]`, `dict[K, V]`, `set[T]`, `frozenset[T]`, `tuple[T, ...]` en lugar de las clases deprecadas de `typing`.
- [x] **Generadores y Streams:** Tipado explícito con `AsyncIterator[str]` o `Iterator[DomainEvent]`.
- [x] **Evitar `Any`:** Restringir el uso de `Any` al mínimo indispensable (ej. argumentos dinámicos de herramientas de IA). Usar `object` o `TypeVar` cuando sea posible.
- [x] **Configuración Rigurosa de Pyright:** Activado `typeCheckingMode = "standard"` con reglas estrictas (`reportAssertAlwaysTrue`, `reportSelfClsParameterName`, `reportConstantRedefinition`, `reportDuplicateImport`).

### 3.2. Formato de Docstrings (Google Style)

- [x] Todas las clases públicas, agregados de dominio, métodos de negocio, handlers CQRS y endpoints HTTP incluyen docstrings estructurados conforme a Google Style con secciones `Args:`, `Returns:` y `Raises:`:

```python
def reserve_quota(
    self, tenant_id: TenantId, estimated_cost: Decimal
) -> QuotaReservationResult:
    """Reserves inference budget quota for an upcoming completion request.

    Args:
        tenant_id: Unique domain identifier of the tenant.
        estimated_cost: Projected cost in USD for token execution.

    Returns:
        QuotaReservationResult containing reservation token and remaining balance.

    Raises:
        TenantNotFoundError: If tenant does not exist.
        InsufficientBudgetError: If available balance is less than estimated cost.
    """
```
- [x] **Formalización:** Documentado en [ADR 0018](../../../.agent/architecture/decisions/0018-strict-typing-and-google-docstrings.md).


---

## 4. Estructura y Estandarización de la Suite de Pruebas (`tests/`)

### 4.1. Jerarquía de Pruebas

1. **`tests/unit/`**:
   - Pruebas rápidas (< 1s en total), aisladas, sin I/O, sin base de datos ni broker.
   - Uso de dobles de prueba puros (InMemory Repositories, Fakes).
2. **`tests/integration/`**:
   - Verificación de adaptadores contra instancias reales (MSSQL 2022, RabbitMQ, Alembic migrations).
3. **`tests/e2e/`**:
   - Pruebas de extremo a extremo cubriendo flujos completos de casos de uso (Walkthrough Happy Path, HITL approvals, streaming con reconexión).

### 4.2. Convención de Nombres de Casos de Prueba

- Estilo BDD descriptivo:
  `test_should_<expected_outcome>_when_<condition>()`
  - Ejemplo: `test_should_raise_insufficient_budget_error_when_balance_is_depleted()`
  - Ejemplo: `test_should_mask_pii_credit_card_when_luhn_checksum_is_valid()`

---

## 5. Plan de Ejecución para la Rama de Refactor

| Paso | Alcance | Tareas Principales | Estado |
| :---: | :--- | :--- | :---: |
| **1** | **Dominio & VO** | Congelar dataclasses de Value Objects, unificar excepciones en `src/domain/shared/exceptions.py`, factorías semánticas y encapsulación. | ✅ **Completado ([ADR 0014](../../../.agent/architecture/decisions/0014-domain-layer-standardization-and-clean-arch-polish.md))** |
| **2** | **CQRS Handlers** | Homogeneizar firmas de handlers, protocolos base, Driven Ports (*Port), context managers de UoW y excepciones de aplicación. | ✅ **Completado ([ADR 0015](../../../.agent/architecture/decisions/0015-application-layer-standardization-and-cqrs-polish.md))** |
| **3** | **Adaptadores & Mappers** | Estandarizar adaptadores a `<Technology><Port>Adapter`, métodos `to_domain`/`to_persistence` en mappers y resiliencia de I/O. | ✅ **Completado ([ADR 0016](../../../.agent/architecture/decisions/0016-infrastructure-layer-standardization-and-adapters-polish.md))** |
| **4** | **Interfaces & Routers** | Unificar formato RFC 7807 en exception handlers, modularizar routers a `<entity>_router.py` y verificar decoradores OpenAPI. | ✅ **Completado ([ADR 0017](../../../.agent/architecture/decisions/0017-interfaces-layer-standardization-and-problem-details.md))** |
| **5** | **Docstrings & Tipado** | Aplicar tipado estricto en Pyright (`typeCheckingMode = "standard"` + reglas estrictas) y docstrings estilo Google. | ✅ **Completado ([ADR 0018](../../../.agent/architecture/decisions/0018-strict-typing-and-google-docstrings.md))** |
| **6** | **Quality Gate** | Ejecución completa de `make check-all` garantizando 0 regresiones. | ✅ **Completado (658 tests verdes, Ruff/Pyright/Bandit 100%)** |

