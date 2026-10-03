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

### 2.1. Capa de Dominio (`src/domain/`)

- **Regla Inquebrantable:** Cero dependencias de librerías externas o frameworks (FastAPI, SQLModel, SQLAlchemy, Pydantic no-puro, AnyIO).
- **Value Objects:**
  - Deben ser inmutables utilizando `@dataclass(frozen=True)` o clases inmutables con validación estricta en `__post_init__`.
  - Deben proveer métodos factoría semánticos (`create()`, `from_raw()`, etc.) y métodos de comparación por valor.
- **Entidades y Agregados (Aggregate Roots):**
  - Identificador único tipado (ej. `TenantId`, `ConversationId`).
  - Estado encapsulado: atributos privados protegidos (`_balance`, `_messages`) con propiedades públicas de solo lectura.
  - Mutación exclusiva a través de métodos de negocio que validen invariantes y emitan Domain Events (`record_event(...)`).
- **Domain Events:**
  - Nomenclatura en pasado imperativo: `<Aggregate><Action>DomainEvent` (ej. `SafetyViolationBlockedDomainEvent`, `MessageAppendedDomainEvent`).
  - Carga útil (`payload`) inmutable y serializable.
- **Excepciones de Dominio:**
  - Jerarquía clara heredando de una clase base común `DomainException` o `DomainError`.

### 2.2. Capa de Aplicación (`src/application/`)

- **Separación CQRS:**
  - **Commands:** Mutan estado, retornan DTOs de resultado o `None`. Nomenclatura: `<Action>Command` y `<Action>CommandHandler`.
  - **Queries:** Solo lectura, no generan efectos secundarios. Nomenclatura: `<Entity>Query` y `<Entity>QueryHandler`.
- **Puertos (Driven Ports):**
  - Interfaces abstractas puras utilizando `typing.Protocol` o `abc.ABC`.
  - Nomenclatura: `<Resource>RepositoryPort`, `<Service>Port`, `<Client>Port`.
- **Unit of Work (UoW):**
  - Context manager explícito (`with unit_of_work as uow:`) que agrupa repositorios bajo una misma transacción y confirma con `uow.commit()`.

### 2.3. Capa de Infraestructura (`src/infrastructure/`)

- **Adaptadores:**
  - Nomenclatura explícita: `<Technology><Port>Adapter` (ej. `MssqlIncidentRepository`, `RabbitMqEventPublisherAdapter`, `RegexPiiScannerAdapter`).
- **Persistencia y Modelos ORM:**
  - Separación rigurosa entre modelos de base de datos (`*Model` en SQLModel/SQLAlchemy) y entidades de dominio.
  - Mappers dedicados (`*Mapper`) con métodos estáticos `to_domain()` y `to_persistence()`.
- **Resiliencia de Conexiones:**
  - Políticas de timeout, retries exponenciales y manejo de desconexión transitoria en operaciones de I/O.

### 2.4. Capa de Interfaces (`src/interfaces/`)

- **Controladores y Routers:**
  - Nomenclatura de routers: `<entity>_router.py`.
  - Los endpoints HTTP deben delegar inmediatamente en Application Handlers o Servicios coordinadores; prohibido escribir lógica de negocio en routers.
- **DTOs y Esquemas (Pydantic v2):**
  - Distinción entre Requests (`*Request`) y Responses (`*Response`).
  - Decoradores y validaciones con `Field(...)`, `minLength`, `maxLength`, `description` y `examples`.
- **Estandarización de Errores HTTP:**
  - Respuestas de error uniformes basadas en **RFC 7807 (Problem Details)**:

    ```json
    {
      "type": "urn:problem:safety-policy-violation",
      "title": "Safety Policy Violation",
      "status": 400,
      "detail": "Prompt injection detected.",
      "code": "PROMPT_INJECTION_DETECTED"
    }
    ```

---

## 3. Estándar de Tipado Estricto y Docstrings

### 3.1. Tipado Estático (Python 3.12+ / Pyright)

- **Uniones Modernas:** Utilizar siempre el operador `|` en lugar de `Union[A, B]` u `Optional[A]`.
- **Colecciones Built-in:** Utilizar `list[T]`, `dict[K, V]`, `set[T]`, `tuple[T, ...]` en lugar de las clases deprecadas de `typing`.
- **Generadores y Streams:** Tipado explícito con `AsyncIterator[str]` o `Iterator[DomainEvent]`.
- **Evitar `Any`:** Restringir el uso de `Any` al mínimo indispensable (ej. argumentos dinámicos de herramientas de IA). Usar `object` o `TypeVar` cuando sea posible.

### 3.2. Formato de Docstrings (Google Style)

Todas las clases públicas, métodos de negocio y endpoints deben incluir docstrings con estructura canónica:

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

| Paso | Alcance | Tareas Principales |
| :---: | :--- | :--- |
| **1** | **Dominio & VO** | Congelar dataclasses de Value Objects, unificar excepciones en `src/domain/shared/exceptions.py`. |
| **2** | **CQRS Handlers** | Homogeneizar firmas de handlers, inyección de dependencias y context managers de UoW. |
| **3** | **Adaptadores & Mappers** | Revisar mapeo exhaustivo entre modelos SQLModel y entidades DDD. |
| **4** | **Interfaces & Routers** | Unificar formato RFC 7807 en exception handlers, verificar decoradores OpenAPI. |
| **5** | **Docstrings & Tipado** | Aplicar tipado estricto en Pyright con `reportUnknownMemberType` y docstrings estilo Google. |
| **6** | **Quality Gate** | Ejecución completa de `make check-all` garantizando 0 regresiones. |
