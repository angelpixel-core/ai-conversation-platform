# Roadmap de Implementación — Slice 6: Multi-Tenant Policy Engine, Dynamic Model Routing & Cost Budgets

Este documento detalla la ruta de desarrollo, aislamiento multi-inquilino (*Multi-Tenancy*), motor de políticas de consumo, enrutamiento dinámico de LLMs según costo/latencia y control presupuestario transaccional sobre **Microsoft SQL Server (MSSQL)**, **AnyIO** y **RabbitMQ**.

---

## 🎯 Objetivo del Slice 6

Evolucionar la plataforma hacia una solución SaaS Enterprise multi-inquilino con altos estándares de gobernanza:

1. **Aislamiento Multi-Tenant Estricto (Data Segregation):** Garantizar la segregación lógica de datos de conversaciones, mensajes, métricas y outbox a nivel de base de datos (`tenant_id`), aplicando filtrado contextual transparente y defensivo en repositorios MSSQL e índices compuestos (`(tenant_id, id)` y `(tenant_id, created_at)`).
2. **Control Presupuestario Atómico en MSSQL (`WITH (ROWLOCK, UPDLOCK)`):** Validar y reservar saldo/tokens atómicamente en SQL Server antes de autorizar la inferencia hacia el worker de RabbitMQ, bloqueando condiciones de carrera (*double-spending*) y rechazando peticiones con `402 Payment Required` si el inquilino excede su cuota contratada.
3. **Propagación Asíncrona de Contexto con AnyIO:** Orquestar chequeos de cuotas, políticas y fallbacks de proveedores mediante `contextvars` y `anyio.create_task_group()`, manteniendo la aislación y trazabilidad entre requests y tareas hijas.
4. **Motor de Enrutamiento Dinámico de Modelos (Dynamic Model Router & Fallback Gateway):** Dirigir las peticiones a distintos modelos o proveedores (ej. modelos económicos/rápidos vs. modelos de razonamiento) según reglas del tenant, con conmutación por contingencia (*fallback*) transparente ante degradación del proveedor primario.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente HTTP ]
       │  (1. Request con Headers 'X-Tenant-ID' y 'Authorization')
       ▼
[ FastAPI Tenant Middleware ]
       │  (2. Extrae y propaga TenantContext mediante contextvars / AnyIO)
       ▼
[ Application Layer: Policy & Router Engine ]
       │  (3. Evalúa cuota en MSSQL: 'ReserveQuotaCommand' con WITH (ROWLOCK, UPDLOCK))
       ▼
[ MSSQL (Tenant Balances & Policies) ]
       │  (4. Aprobado -> Selecciona Provider/Model según regla del Tenant)
       ▼
[ Outbox Table (MSSQL) ]
       │  (5. Inserta MessageAppendedDomainEvent con metadata de Tenant & Routing)
       ▼
[ RabbitMQ Topic Exchange ('ai_platform.conversations') ]
       │  (6. Worker consume evento con routing key enriquecida con tenant_id)
       ▼
[ Dynamic LLM Gateway Adapter (Provider A / Fallback Provider B vía AnyIO) ]
       │  (7. Emite stream -> Registra buffer SSE e infiere tokens reales)
       ▼
[ SettleQuotaCommand (Ajusta y liquida balance final del Tenant en MSSQL) ]
```

---

## 📋 Lista de Tareas y Fases de Implementación

### Fase 1: Dominio y Reglas de Tenancy, Routing y Budgets

*Invariantes de inquilinos, límites de gasto y contratos de routing puros en Python (Clean Architecture).*

- [x] **Value Objects de Tenancy y Presupuesto**
  - Archivo: `src/domain/tenants/value_objects/tenant_id.py` (Slug/alfanumérico inmutable, 3..64 caracteres, sin dependencias externas).
  - Archivo: `src/domain/tenants/value_objects/monetary_budget.py` (`Decimal`, saldo disponible, moneda USD, operaciones de reserva/deducción/reembolso).
  - Archivo: `src/domain/routing/value_objects/model_route.py` (Proveedor, `model_id`, coste por 1.000 tokens, `fallback_model_id`, tier mínimo).
- [ ] **Entidades de Dominio: Tenant & TenantPolicy**
  - Archivo: `src/domain/tenants/entities/tenant.py` (`AggregateRoot` con balance, estado, políticas y métodos `reserve_tokens()`, `settle_actual_cost()`, `suspend()`).
  - Archivo: `src/domain/tenants/entities/tenant_policy.py` (Tier `FREE`/`STANDARD`/`ENTERPRISE`, max tokens por petición, modelos autorizados).
- [ ] **Eventos de Dominio de Presupuesto y Enrutamiento**
  - Archivo: `src/domain/tenants/events/tenant_events.py` (`TenantQuotaExceededDomainEvent`, `TenantBudgetReservedDomainEvent`, `TenantBudgetSettledDomainEvent`, `ModelRouteFallbackActivatedDomainEvent`).
- [ ] **Puertos de Persistencia y Catálogo (Driven Ports)**
  - Archivo: `src/domain/tenants/ports/tenant_repository_port.py` (Contrato abstracto: `get_by_id`, `save`, `reserve_budget_atomic`).
  - Archivo: `src/domain/routing/ports/model_catalog_port.py` (Contrato abstracto para catálogo de modelos y capacidades).
- [ ] **Tests Unitarios de Dominio**
  - Archivos:
    - `tests/unit/domain/test_tenant_id.py`
    - `tests/unit/domain/test_monetary_budget.py`
    - `tests/unit/domain/test_model_route.py`
    - `tests/unit/domain/test_tenant_entity.py`
    - `tests/unit/domain/test_tenant_events.py`
    - `tests/unit/domain/test_tenant_repository_port.py`
    - `tests/unit/domain/test_model_catalog_port.py`

---

### Fase 2: Capa de Aplicación (Policy Enforcement & Routing Services)

*Orquestación con AnyIO para validaciones concurrentes, comandos CQRS y propagación de contexto.*

- [ ] **Servicio de Contexto de Inquilino (`TenantContext`)**
  - Archivo: `src/application/shared/tenancy/tenant_context.py` (basado en `contextvars.ContextVar[TenantId | None]`, compatible con tareas AnyIO).
- [ ] **Servicio de Aplicación: Dynamic Model Router**
  - Archivo: `src/application/routing/services/model_router_service.py` (Evalúa políticas de tenant, coste vs. latencia, tamaño de contexto y selección de fallback).
- [ ] **Comandos CQRS de Gestión de Cuotas**
  - Archivo: `src/application/tenants/commands/reserve_quota_command.py` (`ReserveQuotaCommand`, `ReserveQuotaResult`, `ReserveQuotaCommandHandler`).
  - Archivo: `src/application/tenants/commands/settle_quota_command.py` (`SettleQuotaCommand`, `SettleQuotaResult`, `SettleQuotaCommandHandler`).
- [ ] **Ampliación del Puerto `UnitOfWork`**
  - Archivo: `src/application/shared/ports/unit_of_work.py` (Incorpora propiedad `tenants: TenantRepositoryPort`).
- [ ] **Tests Unitarios de Aplicación**
  - Archivos:
    - `tests/unit/application/test_tenant_context.py`
    - `tests/unit/application/test_model_router_service.py`
    - `tests/unit/application/test_reserve_quota_command.py`
    - `tests/unit/application/test_settle_quota_command.py`

---

### Fase 3: Infraestructura MSSQL Multi-Tenant y Bloqueos Pesimistas

*Aislamiento transaccional, índices compuestos y concurrencia segura en SQL Server.*

- [ ] **Modelos ORM Físicos en MSSQL (`src/infrastructure/persistence/mssql/models.py`)**
  - Incorporar `TenantModel` (tabla `tenants`: `id`, `name`, `status`, `balance_usd`, `currency`, `created_at`, `updated_at`).
  - Incorporar `TenantPolicyModel` (tabla `tenant_policies`: `tenant_id`, `tier`, `max_tokens_per_request`, `monthly_budget_usd`, `allowed_models_json`).
  - Actualizar `ConversationModel`, `AuditLogModel` y `StreamBufferChunkModel` incorporando columna indexada `tenant_id: str = Field(index=True, max_length=64, nullable=False)` e índices compuestos `(tenant_id, id)`.
- [ ] **Mapeador de Datos Relacional (`TenantMapper`)**
  - Archivo: `src/infrastructure/persistence/mssql/tenant_mapper.py` (Mapeo bidireccional entre la entidad `Tenant` y los modelos SQLModel).
- [ ] **Adaptadores de Repositorio MSSQL e In-Memory**
  - Archivo: `src/infrastructure/persistence/mssql/tenant_repository.py` (Implementa `MssqlTenantRepository` utilizando `SELECT ... WITH (ROWLOCK, UPDLOCK)` para reservas atómicas).
  - Archivo: `src/infrastructure/persistence/in_memory/tenant_repository.py` (`InMemoryTenantRepositoryAdapter` para tests unitarios ultrarrápidos).
- [ ] **Actualización de `MssqlUnitOfWork` e `InMemoryUnitOfWork`**
  - Integrar propiedad `tenants` en ambos adaptadores transaccionales.
- [ ] **Migración de Esquema Alembic para MSSQL**
  - Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0003_multi_tenant_and_budgets.py` (con `down_revision = "0002_enterprise_auditing_and_idempotency"`).
- [ ] **Tests Unitarios y de Integración MSSQL**
  - Archivos:
    - `tests/unit/infrastructure/mssql/test_tenant_model.py`
    - `tests/unit/infrastructure/mssql/test_tenant_mapper.py`
    - `tests/unit/infrastructure/mssql/test_mssql_tenant_repository.py`
    - `tests/integration/infrastructure/mssql/test_tenant_isolation.py`
    - `tests/integration/infrastructure/mssql/test_concurrent_budget_reservations.py`

---

### Fase 4: RabbitMQ Multi-Tenant Routing con AnyIO

*Segmentación de topics, enriquecimiento de eventos y fallback resiliente en workers.*

- [ ] **Enriquecimiento de Eventos y Topología de RabbitMQ**
  - Archivo: `src/infrastructure/messaging/rabbitmq/rabbitmq_topology_config.py` (Soporte de routing keys multi-tenant: `ai_platform.conversations`, binding `tenant.*.*.conversation.*` o `conversations.{tenant_id}.*`).
- [ ] **Worker Asíncrono Multi-Tenant con Fallback AnyIO**
  - Actualizar `src/application/conversations/workers/llm_message_processing_worker.py` para:
    - Extraer `tenant_id` y activar `TenantContext`.
    - Liquidar cuota real (`SettleQuotaCommand`) tras la inferencia.
    - Ejecutar fallback de proveedor LLM bajo `anyio.create_task_group()` en caso de degradación o fallo transitorio.
- [ ] **Tests de Integración Worker + RabbitMQ**
  - Archivos:
    - `tests/unit/application/test_tenant_aware_worker.py`
    - `tests/integration/workers/test_tenant_routing_worker.py`

---

### Fase 5: Interfaces HTTP & Middlewares de FastAPI

*Extracción de cabeceras, códigos HTTP empresariales y Swagger segregado.*

- [ ] **Middleware de Contexto de Inquilino (`TenantContextMiddleware`)**
  - Archivo: `src/interfaces/http/middlewares/tenant_context_middleware.py` (Inspecciona `X-Tenant-ID`, rechaza peticiones no identificadas con `400 Bad Request` en rutas protegidas y administra el ciclo de vida del `TenantContext`).
- [ ] **Dependencia FastAPI de Inquilino (`get_current_tenant_id`)**
  - Archivo: `src/interfaces/http/dependencies/tenant_dependency.py` (Inyección tipada para controladores que requieran el inquilino activo).
- [ ] **Router de Administración de Tenants y Políticas**
  - Archivo: `src/interfaces/http/routers/tenant_admin_router.py`
    - `GET /admin/tenants/{id}/budget` (`200 OK`)
    - `PATCH /admin/tenants/{id}/policy` (`200 OK`)
- [ ] **Manejo Centralizado de Excepciones de Cuota**
  - Mapear `TenantQuotaExceededDomainEvent` / `TenantQuotaExceededError` a `HTTP 402 Payment Required` con detalle del saldo y política.
- [ ] **Tests Unitarios e Integración HTTP**
  - Archivos:
    - `tests/unit/interfaces/http/test_tenant_context_middleware.py`
    - `tests/unit/interfaces/http/test_tenant_dependency.py`
    - `tests/integration/api/test_tenant_middleware_isolation.py`
    - `tests/integration/api/test_budget_exceeded_rejection.py`

---

### Fase 6: Ensamble, Container y Documentación de Decisiones

- [ ] **Actualización del Composition Root (`src/container.py` y `src/worker_container.py`)**
  - Cableado de `TenantRepositoryPort`, `ModelCatalogPort`, `ModelRouterService`, `TenantContextMiddleware` y comandos de cuota.
- [ ] **Documento de Decisión Arquitectónica (ADR 0005)**
  - Archivo: `.agent/architecture/decisions/0005-multi-tenancy-dynamic-routing-and-budget-controls.md` (Aceptado).
- [ ] **Actualización del Diagrama Vivo del Sistema**
  - Archivo: `.agent/architecture/system-map.mermaid.md` (Reflejar capa de Tenants, Model Router, bloqueos MSSQL y middleware).

---

## 📐 Plantillas Canónicas del Slice 6 (`.agent/templates/`)

Para estandarizar el desarrollo y permitir la generación autónoma asistida por subagentes en TDD estricto, se extraen los siguientes templates canónicos con sus respectivos contratos de prueba:

| Capa | Template de Producción (`.tt.py`) | Template de Pruebas Unitarias (`test_*.tt.py`) |
| :--- | :--- | :--- |
| **Domain VOs** | `.agent/templates/domain/value_objects/tenant_id.tt.py`<br>`.agent/templates/domain/value_objects/monetary_budget.tt.py`<br>`.agent/templates/domain/value_objects/model_route.tt.py` | `.agent/templates/domain/value_objects/test_tenant_id.tt.py`<br>`.agent/templates/domain/value_objects/test_monetary_budget.tt.py`<br>`.agent/templates/domain/value_objects/test_model_route.tt.py` |
| **Domain Entities** | `.agent/templates/domain/entities/tenant_entity.tt.py`<br>`.agent/templates/domain/events/tenant_events.tt.py` | `.agent/templates/domain/entities/test_tenant_entity.tt.py`<br>`.agent/templates/domain/events/test_tenant_events.tt.py` |
| **Domain Ports** | `.agent/templates/domain/ports/tenant_repository_port.tt.py`<br>`.agent/templates/domain/ports/model_catalog_port.tt.py` | `.agent/templates/domain/ports/test_tenant_repository_port.tt.py`<br>`.agent/templates/domain/ports/test_model_catalog_port.tt.py` |
| **Application** | `.agent/templates/application/shared/tenant_context.tt.py`<br>`.agent/templates/application/services/model_router_service.tt.py`<br>`.agent/templates/application/commands/reserve_quota_command.tt.py` | `.agent/templates/application/shared/test_tenant_context.tt.py`<br>`.agent/templates/application/services/test_model_router_service.tt.py`<br>`.agent/templates/application/commands/test_reserve_quota_command.tt.py` |
| **Infrastructure** | `.agent/templates/infrastructure/persistence/sqlmodel/tenant_model.tt.py`<br>`.agent/templates/infrastructure/persistence/sqlmodel/tenant_mapper.tt.py`<br>`.agent/templates/infrastructure/persistence/sqlmodel/mssql_tenant_repository.tt.py` | `.agent/templates/infrastructure/persistence/sqlmodel/test_tenant_model.tt.py`<br>`.agent/templates/infrastructure/persistence/sqlmodel/test_tenant_mapper.tt.py`<br>`.agent/templates/infrastructure/persistence/sqlmodel/test_mssql_tenant_repository.tt.py` |
| **Interfaces HTTP** | `.agent/templates/interfaces/http/tenant_context_middleware.tt.py`<br>`.agent/templates/interfaces/http/tenant_dependency.tt.py` | `.agent/templates/interfaces/http/test_tenant_context_middleware.tt.py`<br>`.agent/templates/interfaces/http/test_tenant_dependency.tt.py` |

---

## 🔍 Criterios de Aceptación del Slice 6

1. **Aislamiento Total de Inquilinos:** Un `GET /conversations` del Tenant A jamás retorna ni filtra registros del Tenant B, garantizado a nivel de repositorio y por el scoping de tenant en MSSQL.
2. **Control de Presupuesto Concurrente:** Si un tenant dispone de saldo para exactamente una petición y dispara dos solicitudes simultáneas, solo una procede; la segunda es rechazada con `402 Payment Required` sin saldo negativo gracias al bloqueo `WITH (ROWLOCK, UPDLOCK)` en MSSQL.
3. **Fallback Automático de Modelos:** Si el proveedor principal configurado para un tenant entra en degradación o timeout, el worker conmuta de forma transparente al modelo de contingencia definido en la política del tenant usando AnyIO.
4. **Validación AnyIO:** La suite de pruebas valida la orquestación concurrente bajo `anyio.from_thread` y `anyio.create_task_group()` sin incurrir en deadlocks ni bloqueos en el pool de conexiones de MSSQL.
5. **Calidad y Cobertura 100% Verde:** `make check-all` (Ruff, Pyright, Bandit, Pytest) finaliza con código de salida `0`.
