# RFC-32: Especificación y Descargo de Adopción del Contrato Multi-Tenant (`/admin/tenants`)

- **RFC Number:** RFC-32
- **Título:** Especificación del Contrato de Gestión, Aislamiento y Metadatos de Inquilinos Multi-Tenant
- **Fecha:** 2026-10-15
- **Autores:** Equipo Frontend Portal (`apps/chatbot/web/portal`) & Core Architecture Team (`apps/chatbot/service/api`)
- **Destinatarios:** Equipo Frontend Portal, Backend Core, Operaciones e Infraestructura
- **Estado:** ✅ ACEPTADO E IMPLEMENTADO (Adopted & Implemented in `feat/multi-tenant-administration-contract`)
- **Caso de Uso Vinculado:** [CU-02: Aislamiento y Contexto Multi-Tenant](../12-cu-02-multi-tenant-administration-and-isolation.md)
- **ADR Vinculado:** [ADR 0021](../../../.agent/architecture/decisions/0021-multi-tenant-contract-standardization-and-cqrs-isolation.md)

---

## 1. Resumen Ejecutivo y Declaración de Conformidad

Este documento certifica la adopción formal e implementación completa del **RFC-32** propuesto por el equipo de Frontend Portal Web. El motor conversacional backend (`apps/chatbot/service/api`) ha unificado y estandarizado el contrato HTTP bajo `/admin/tenants`, eliminando las asimetrías de nomenclatura históricas, extendiendo los niveles de servicio y garantizando aislamiento absoluto sin introducir roturas retrospectivas (*zero breaking changes*).

El desarrollo fue ejecutado bajo los principios de **Clean Architecture**, **Domain-Driven Design (DDD)** y **CQRS**, formalizado en el **ADR 0021** y verificado con el 100% de la suite de pruebas automatizadas en verde.

---

## 2. Matriz de Compatibilidad y Resolución de Asimetrías

Para permitir una migración fluida del Frontend sin requerir despliegues acoplados, se implementó el patrón de **Lector Tolerante y Escritor Dual (*Tolerant Reader & Dual Writer*)**:

### 2.1. Dual-Identifier Compatibility en Respuestas
Toda respuesta emitida por el backend expone **simultáneamente** el identificador canónico `id` y su alias compatible `tenant_id`:

```json
{
  "id": "corp-acme",
  "tenant_id": "corp-acme",
  "name": "ACME Corporation"
}
```

Aplica a los endpoints:
- `GET /admin/tenants` (`TenantSummaryResponse`)
- `POST /admin/tenants` (`TenantBudgetResponse`)
- `GET /admin/tenants/{id}/budget` (`TenantBudgetResponse`)
- `PATCH /admin/tenants/{id}/policy` (`TenantPolicyResponse`)
- `POST /admin/tenants/{id}/reserve` (`ReserveQuotaResponse`)

### 2.2. Tolerancia en Cargas Útiles de Entrada (`POST /admin/tenants`)
El endpoint de aprovisionamiento acepta indistintamente:
- `id` (nomenclatura canónica recomendada).
- `tenant_id` (nomenclatura retrocompatible).
- Si ambos son enviados, `id` tiene precedencia.

### 2.3. Estructura Dual: Campos Planos y Subobjetos Enriquecidos
En `GET /admin/tenants`, el Frontend puede continuar consumiendo los campos planos directos o migrar a los nuevos subobjetos modulares para paneles de visualización:

| Campo Legacy (Plano) | Subobjeto RFC-32 Enriquecido | Descripción |
| :--- | :--- | :--- |
| `balance` | `financials.balance` | Saldo monetario actual asignado al inquilino (USD). |
| `reserved_amount` | `financials.reserved_amount` | Saldo temporalmente retenido por inferencias en curso. |
| `available_balance` | `financials.available_balance` | Balance disponible operativo (`balance - reserved_amount`). |
| `currency` | `financials.currency` | Código de moneda ISO 4217 (por defecto `USD`). |
| N/A | `financials.monthly_budget_usd` | Techo presupuestario asignado para el período mensual. |
| N/A | `limits.max_tokens_per_request` | Techo máximo de tokens por llamada según el Tier. |
| N/A | `limits.max_requests_per_minute` | Tasa de solicitudes por minuto asignada al tenant. |
| N/A | `metadata.contact_email` | Correo corporativo del administrador del tenant. |
| N/A | `metadata.created_at` | Timestamp ISO 8601 UTC de creación del inquilino. |
| N/A | `metadata.updated_at` | Timestamp ISO 8601 UTC de última modificación. |

---

## 3. Catálogo Extendido de Tiers y Políticas

Se oficializa el nivel de servicio **`PRO`** solicitado en el RFC-32, consolidando la matriz de tiers:

| Tier | Límite Tokens / Req | RPM por Defecto | Presupuesto Mensual Base | Modelos Habilitados por Defecto |
| :---: | :---: | :---: | :---: | :--- |
| **`FREE`** | 2,048 tokens | 30 req/min | $50.00 USD | `["gpt-4o-mini"]` |
| **`STANDARD`** | 4,096 tokens | 60 req/min | $300.00 USD | `["gpt-4o-mini", "gemini-1.5-flash"]` |
| **`PRO`** | **8,192 tokens** | **120 req/min** | **$1,000.00 USD** | `["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"]` |
| **`ENTERPRISE`** | 16,384 tokens | 300 req/min | $5,000.00 USD | Todos los modelos disponibles |

---

## 4. Guía Rápida de Endpoints e Integración HTTP

### 4.1. Listar Inquilinos Registrados
- **Ruta:** `GET /admin/tenants`
- **Cabeceras:** No requiere `X-Tenant-ID`.
- **Respuesta Exitosa (`200 OK`):**
```json
[
  {
    "id": "corp-acme",
    "tenant_id": "corp-acme",
    "name": "ACME Corporation",
    "status": "ACTIVE",
    "tier": "PRO",
    "balance": "750.0000",
    "reserved_amount": "15.0000",
    "available_balance": "735.0000",
    "currency": "USD",
    "financials": {
      "currency": "USD",
      "balance": "750.0000",
      "reserved_amount": "15.0000",
      "available_balance": "735.0000",
      "monthly_budget_usd": "1000.0000"
    },
    "limits": {
      "max_tokens_per_request": 8192,
      "max_requests_per_minute": 120
    },
    "metadata": {
      "created_at": "2026-09-15T10:00:00Z",
      "updated_at": "2026-10-15T15:30:00Z",
      "contact_email": "admin@acme.corp"
    }
  }
]
```

### 4.2. Aprovisionar Nuevo Inquilino
- **Ruta:** `POST /admin/tenants`
- **Cuerpo de Solicitud (`CreateTenantRequest`):**
```json
{
  "id": "corp-globex",
  "name": "Globex Corporation",
  "tier": "PRO",
  "balance_usd": "500.00",
  "monthly_budget_usd": "1000.00",
  "max_tokens_per_request": 8192,
  "max_requests_per_minute": 120,
  "contact_email": "ops@globex.com",
  "allowed_models": ["gpt-4o", "gemini-1.5-pro"]
}
```
- **Respuesta Exitosa (`201 Created`):**
```json
{
  "id": "corp-globex",
  "tenant_id": "corp-globex",
  "balance": "500.0000",
  "reserved_amount": "0.0000",
  "available_balance": "500.0000",
  "currency": "USD"
}
```

### 4.3. Consultar Estado Presupuestario
- **Ruta:** `GET /admin/tenants/{id}/budget`
- **Respuesta Exitosa (`200 OK`):**
```json
{
  "id": "corp-globex",
  "tenant_id": "corp-globex",
  "balance": "500.0000",
  "reserved_amount": "0.0000",
  "available_balance": "500.0000",
  "currency": "USD"
}
```

### 4.4. Actualizar Política de Gobernanza
- **Ruta:** `PATCH /admin/tenants/{id}/policy`
- **Cuerpo de Solicitud (`UpdateTenantPolicyRequest`):**
```json
{
  "tier": "ENTERPRISE",
  "max_tokens_per_request": 16384,
  "monthly_budget_usd": "2500.00",
  "max_requests_per_minute": 240,
  "allowed_models": ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]
}
```
- **Respuesta Exitosa (`200 OK`):**
```json
{
  "id": "corp-globex",
  "tenant_id": "corp-globex",
  "tier": "ENTERPRISE",
  "max_tokens_per_request": 16384,
  "monthly_budget_usd": "2500.0000",
  "max_requests_per_minute": 240,
  "allowed_models": ["claude-3-5-sonnet", "gemini-1.5-pro", "gpt-4o"]
}
```

### 4.5. Reserva Atómica de Cuota
- **Ruta:** `POST /admin/tenants/{id}/reserve`
- **Cuerpo de Solicitud:**
```json
{
  "estimated_cost": "0.0500",
  "model_id": "gpt-4o"
}
```
- **Respuesta Exitosa (`200 OK`):**
```json
{
  "id": "corp-globex",
  "tenant_id": "corp-globex",
  "reserved_cost": "0.0500",
  "remaining_balance": "499.9500"
}
```

---

## 5. Aislamiento y Reglas de Middleware (`X-Tenant-ID`)

1. **Rutas Administrativas (`/admin/*`):** Están exentas de la cabecera `X-Tenant-ID`. El identificador se recibe explícitamente vía URL `{id}` o cuerpo JSON.
2. **Rutas de Negocio (`/conversations`, etc.):** Continúan exigiendo estrictamente la cabecera `X-Tenant-ID` (o `X-Tenant-Id`). La omisión rechaza la llamada con `HTTP Status: 400 Bad Request`.

---

## 6. Verificación de Calidad y Artefactos Disponibles

- **Documentación Interactiva ReDoc / OpenAPI 3.1:** Exportada y disponible en `public/openapi.json` y `public/index.html`.
- **Base de Datos:** Migración Alembic `0008_tenant_metadata_and_rate_limits.py` lista para despliegue en ambientes compartidos.
- **Pruebas de Regresión:**
  - `tests/unit/interfaces/http/test_tenant_schemas.py`: 5 tests unitarios cubriendo serialización y tolerancia.
  - `tests/integration/api/test_tenant_admin_router.py`: 7 pasos end-to-end verificando creación, alias, parche de políticas y reservas.
  - `make check-all`: 100% verde (666 tests ejecutados, 0 linter warnings, 0 type errors).
