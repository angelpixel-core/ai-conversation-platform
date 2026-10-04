# ADR 0017: Estandarización de la Capa de Interfaces, Problem Details (RFC 7807), Modularización de Routers y DTOs Pydantic v2

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `refactor/source-code-and-clean-arch-polish` — Sección 2.4 y Paso 4 de RFC 02

---

## 1. Contexto y Problemática

En la arquitectura Clean / Hexagonal (Ports & Adapters) de `ai-conversation-platform`, la **Capa de Interfaces (`src/interfaces/`)** alberga los adaptadores primarios o conductores (**Driver Adapters**), primordialmente los endpoints HTTP sobre FastAPI, middlewares de contexto/observabilidad y esquemas de transferencia de datos (DTOs) en Pydantic v2.

Durante la revisión integral de código (RFC 02), se identificaron las siguientes oportunidades de mejora:

1. **Gestión Heterogénea de Errores HTTP:**
   - La API utilizaba una mezcla de excepciones `HTTPException` ad-hoc de FastAPI (con estructura `{"detail": "..."}`) y handlers específicos (como `SafetyPolicyViolationError` con diccionario custom `{"error": "...", "violation_type": "..."}`).
   - No existía adopción formal del estándar internacional **RFC 7807 (Problem Details for HTTP APIs)**, que define un formato canónico, predecible e interoperable para reportar errores en APIs RESTful mediante el tipo de contenido `application/problem+json`.
2. **Centralización Excesiva en `api.py`:**
   - El archivo `src/interfaces/http/api.py` contenía más de 350 líneas de transporte dedicadas al registro de rutas de conversaciones, despacho de mensajes y streaming SSE (`_register_conversation_routes`, `_register_message_routes`, `_register_streaming_routes`), rompiendo la modularidad del subpaquete `src/interfaces/http/routers/` donde ya residían `approvals_router.py`, `governance_router.py`, `knowledge_router.py`, `tenant_admin_router.py` y `workflows_router.py`.
3. **Nomenclatura y Metadatos de DTOs:**
   - Ciertos esquemas Pydantic no se alineaban con la convención canónica `<Entity>Request` y `<Entity>Response` (ej. `CitationSchema`, `AgentActivityEventSchema`), y requerían enriquecimiento de validaciones de campo (`min_length`, `max_length`, `description`, `examples`) para una documentación OpenAPI interactiva de primer nivel.

---

## 2. Decisión de Diseño

Se aprueba y ejecuta la estandarización canónica de la Capa de Interfaces conforme a los siguientes lineamientos:

### 2.1. Adopción de RFC 7807 (Problem Details for HTTP APIs)

Se introduce el módulo `src/interfaces/http/problem_details.py` con:

1. **Modelo Canónico Pydantic v2 `ProblemDetails`:**
   - `type: str`: URI absoluta o relativa que identifica el tipo de problema (por defecto `"about:blank"` o esquemas `urn:problem:*`).
   - `title: str`: Resumen breve y legible por humanos del tipo de problema.
   - `status: int`: Código de estado HTTP correspondiente (400, 402, 403, 404, 409, 422, 500).
   - `detail: str`: Explicación detallada de la ocurrencia específica.
   - `code: str | None`: Código de error canónico en `SCREAMING_SNAKE_CASE` (ej. `PROMPT_INJECTION_DETECTED`, `CONVERSATION_NOT_FOUND`, `IDEMPOTENCY_CONFLICT`).
   - `instance: str | None`: URI opcional de la ocurrencia específica.
   - **Extensiones de Retrocompatibilidad:** Campos `error` y `message`, además de soporte abierto para metadatos contextuales (`violation_type`, `risk_score`, `matched_rule`, `incident_id`, etc.).

2. **Fábrica de Respuestas `problem_details_response(...)`:**
   - Construye instancias de `JSONResponse` con cabecera `Content-Type: application/problem+json`.
   - Garantiza que clientes legados que esperan `data["error"]` o `data["detail"]` continúen operando sin ninguna alteración ni degradación.

3. **Exception Handlers Globales Unificados en `FastAPI`:**
   - `SafetyPolicyViolationError` -> Status 400 (`urn:problem:safety-policy-violation`, `PROMPT_INJECTION_DETECTED`).
   - `ConversationNotFoundError` / `EntityNotFoundError` -> Status 404 (`urn:problem:conversation-not-found`, `CONVERSATION_NOT_FOUND`).
   - `IdempotencyConflictError` -> Status 409 (`urn:problem:idempotency-conflict`, `IDEMPOTENCY_CONFLICT`).
   - `DomainError` -> Status 400 (`urn:problem:domain-error`, `DOMAIN_INVARIANT_VIOLATION`).

### 2.2. Modularización Canónica de Routers (`<entity>_router.py`)

Se crea `src/interfaces/http/routers/conversations_router.py` conteniendo la función fábrica:
```python
def create_conversations_router(
    create_conversation_handler: CreateConversationHandler | None = None,
    send_message_handler: SendMessageHandler | None = None,
    stream_conversation_handler: StreamConversationQueryHandler | None = None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
    stream_recovery_service: StreamRecoveryService | None = None,
    retriever_service: HybridRetrieverService | None = None,
    unit_of_work: UnitOfWork | None = None,
    guarded_executor: GuardedCommandExecutor | None = None,
) -> APIRouter:
```
- Encapsula las rutas `/conversations`, `/conversations/{id}/messages` y `/conversations/{id}/stream`.
- Aísla la lógica de recuperación de streaming, formato de eventos SSE (`event: citation`, `event: tool_approval_required`) y resolución de fallbacks en caso de reconexión.
- Convierte a `src/interfaces/http/api.py` en un orquestador limpio y desacoplado, reduciendo su tamaño y complejidad ciclomática.
- Se exporta `create_conversations_router` desde `src/interfaces/http/routers/__init__.py`.

### 2.3. Estandarización de DTOs y Esquemas Pydantic v2

- **Convención `<Entity>Request` y `<Entity>Response`:**
  - `CreateConversationRequest`, `ConversationResponse`, `SendMessageRequest`, `MessageResponse` enriquecidos con `Field(..., description=..., examples=...)`.
- **Aliases Retrocompatibles:**
  - `CitationResponse = CitationSchema` en `knowledge_schemas.py`.
  - `AgentActivityEventResponse = AgentActivityEventSchema` en `agents_schemas.py`.
- **Listas `__all__` Explícitas:**
  - Incorporadas en `schemas.py`, `knowledge_schemas.py`, `agents_schemas.py`, `tools_schemas.py` y `governance_schemas.py`.

---

## 3. Consecuencias y Beneficios

1. **Conformidad Estándar Internacional:** Respuestas de error estructuradas conforme a RFC 7807 (`application/problem+json`), simplificando el consumo por frontends, SDKs y clientes de terceros.
2. **Cero Regresiones (100% Retrocompatible):** Ningún contrato HTTP previo fue roto; todos los campos esperados por los tests existentes se conservan como extensiones RFC 7807.
3. **Mantenibilidad y Modularidad:** `src/interfaces/http/routers/` ahora concentra el 100% de la definición de endpoints, organizados homogéneamente bajo el patrón `<entity>_router.py`.
4. **Verificación Automatizada Completa:** Suite de pruebas unitarias dedicada en `tests/unit/interfaces/http/test_problem_details.py` y compatibilidad total con la suite de pruebas del proyecto.

---

## 4. Estado de Cumplimiento

- **RFC 7807 Problem Details:** Implementado en `src/interfaces/http/problem_details.py`.
- **Modularización de Routers:** Completado en `src/interfaces/http/routers/conversations_router.py` y `api.py`.
- **DTOs y Esquemas Pydantic v2:** Actualizados en `src/interfaces/http/*schemas*.py`.
- **Suite de Pruebas Unitarias:** 7 nuevos tests en `tests/unit/interfaces/http/test_problem_details.py`.
- **Diagrama Vivo:** Actualizado en `.agent/architecture/system-map.mermaid.md`.
