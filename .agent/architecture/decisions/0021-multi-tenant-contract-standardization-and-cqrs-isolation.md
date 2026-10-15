# ADR 0021: Estandarización del Contrato Multi-Tenant (RFC-32), Aislamiento CQRS y Extensión de Tiers

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-15
- **Autores:** Core Architecture Team & Web Portal Team
- **Contexto:** Rama `feat/multi-tenant-administration-contract` — Caso de Uso 02 (CU-02) / RFC-32

---

## 1. Contexto y Problemática

El Frontend Web Portal (`apps/chatbot/web/portal`) y servicios integradores consumen las operaciones de gestión administrativa e inspección de organizaciones e inquilinos multi-tenant bajo la ruta `/admin/tenants`.

Durante la auditoría del **CU-02 (Aislamiento y Contexto Multi-Tenant)**, se detectaron las siguientes asimetrías y desviaciones arquitectónicas:

1. **Asimetría de Identificadores (RFC-32):**
   - El endpoint `GET /admin/tenants` exponía el identificador de la organización como `tenant_id`, mientras que `POST /admin/tenants` esperaba `id` como identificador primario y generaba inconsistencias de contrato entre vistas de tabla, modales de creación y llamadas de detalle (`/admin/tenants/{id}/budget`).
2. **Violación de Clean Architecture en Router:**
   - `tenant_admin_router.py` consumía directamente el repositorio `UnitOfWorkPort`, consultando modelos de base de datos o mutando campos de estado privado (`tenant._policy = ...`) directamente en las rutas en lugar de orquestar mediante comandos y consultas CQRS desacoplados.
3. **Catálogo de Tiers Incompleto:**
   - La plataforma soportaba `FREE`, `STANDARD` y `ENTERPRISE`, careciendo del nivel intermedio `PRO` (8,192 tokens/req) solicitado formalmente por el portal y de metadatos de contacto (`contact_email`) y límites de peticiones por minuto (`max_requests_per_minute`).
4. **Acoplamiento de Esquemas HTTP en el Router:**
   - Los modelos de solicitud y respuesta residían inline dentro de `tenant_admin_router.py`, dificultando su reutilización, validación tipada y evolución conforme a esquemas OpenAPI 3.1.

---

## 2. Decisión de Diseño

Se aprueba y formaliza la adopción de **RFC-32**, reestructurando de raíz la capa de administración de inquilinos con estricto apego a Clean Architecture, DDD y CQRS:

### 2.1. Dual-Identifier Compatibility Pattern (Tolerant Reader & Dual Writer)
- **Lectura Canónica:** Toda respuesta HTTP administrativa (`TenantSummaryResponse`, `TenantBudgetResponse`, `TenantPolicyResponse`, `ReserveQuotaResponse`) expone **simultáneamente** los campos canónicos `id` y su alias compatible `tenant_id`:
  ```json
  {
    "id": "corp-acme",
    "tenant_id": "corp-acme",
    "name": "ACME Corporation"
  }
  ```
- **Escritura Tolerante:** `CreateTenantRequest` acepta `id: str | None = None` o `tenant_id: str | None = None`, resolviendo mediante una propiedad validada `resolved_id` que prioriza `id` y recurre a `tenant_id` sin romper clientes legacy.

### 2.2. Esquema Enriquecido y Compatibilidad Retroactiva (RFC-32)
- `TenantSummaryResponse` incluye simultáneamente campos planos de compatibilidad (`balance`, `reserved_amount`, `available_balance`, `currency`) y subobjetos fuertemente tipados (`financials`, `limits`, `metadata`).
- Esto permite al Portal Web migrar gradualmente de un modelo plano a tarjetas visuales modulares de finanzas, gobernanza y metadatos sin disrupción operativa.

### 2.3. Segregación CQRS Estricta en la Capa de Aplicación
- **Queries:**
  - `ListTenantsQuery` y `ListTenantsQueryHandler`: Proyecta `TenantSummaryDTO` enriquecido con cálculos atómicos de balance disponible.
  - `GetTenantBudgetQuery` y `GetTenantBudgetQueryHandler`: Recupera estado presupuestario encapsulado o lanza `TenantNotFoundError`.
- **Commands:**
  - `UpdateTenantPolicyCommand` y `UpdateTenantPolicyCommandHandler`: Actualiza de forma transaccional la política del tenant a través del método de negocio `tenant.update_policy(new_policy)`, emitiendo el evento de dominio `TenantPolicyUpdatedDomainEvent`.
  - `ProvisionTenantCommand` y `ProvisionTenantCommandHandler`: Extendido con `contact_email` y `max_requests_per_minute`, retornando `ProvisionTenantResult` con identificadores duales.

### 2.4. Modularización del Router HTTP (Límites C901 y Separation of Concerns)
- Se extrajeron todos los esquemas Pydantic v2 a [`src/interfaces/http/tenant_schemas.py`](../../src/interfaces/http/tenant_schemas.py).
- Se desacopló [`src/interfaces/http/routers/tenant_admin_router.py`](../../src/interfaces/http/routers/tenant_admin_router.py) en dos registradores especializados:
  - `_register_command_routes`: POST (provisioning), PATCH (policy update), POST (quota reservation).
  - `_register_query_routes`: GET (list all), GET (budget status).
- Todas las rutas delegan exclusivamente en los CQRS Handlers inyectados, garantizando complejidad ciclomática `<= 8` por función y desacoplamiento absoluto de la persistencia física.

### 2.5. Persistencia Relacional y Migración Alembic 0008
- Se agregaron las columnas `contact_email` a la tabla `tenants` y `max_requests_per_minute` a `tenant_policies` en `models.py`.
- Se creó la migración formal de base de datos `0008_tenant_metadata_and_rate_limits.py`.
- `TenantMapper` implementa mapeo bidireccional soportando el tier `PRO`, valores por defecto seguros y round-trip determinista.

---

## 3. Consecuencias y Beneficios

- **Simetría y Coherencia:** Frontend Portal y Backend se alinean 100% sobre el estándar RFC-32 sin romper compatibilidad retrospectiva.
- **Pureza Arquitectónica:** Cero acceso directo a repositorios o mutación de estado privado desde controladores HTTP.
- **Gobernanza Ampliada:** Catálogo formal de 4 tiers (`FREE`, `STANDARD`, `PRO`, `ENTERPRISE`) con techos de tokens oficiales y eventos de dominio auditables.
- **Calidad y Cobertura:** 100% de la suite de pruebas automatizadas pasa en verde, con cero alertas de Ruff, Pyright o Bandit.
