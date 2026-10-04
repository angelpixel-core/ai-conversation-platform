# ADR 0014: Estandarización y Pulido de la Capa de Dominio (Clean Architecture, DDD y Excepciones Unificadas)

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `refactor/source-code-and-clean-arch-polish` — Sección 2.1 y Paso 1 de RFC 02

---

## 1. Contexto y Problemática

Tras la culminación exitosa de los 10 Slices del Roadmap, la capa de dominio (`src/domain/`) consolidó una rica modelización de negocio (agregados, eventos de dominio, value objects y puertos abstractos). No obstante, la evolución incremental generó pequeñas asimetrías de diseño:

1. **Fragmentación en el Manejo de Errores de Dominio:**
   - La clase base [DomainError](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/shared/domain_error.py) residía aislada en `domain_error.py`.
   - Bounded contexts como `tenants` no poseían un módulo propio de excepciones, utilizando `ValueError` genérico para violaciones de invariantes de negocio (cuotas agotadas, tenants suspendidos, recargas negativas).
   - En `conversations`, `Conversation` lanzaba cadenas de texto arbitrarias en `DomainError` en lugar de excepciones semánticas tipadas.
2. **Value Objects sin Métodos Factoría Canónicos:**
   - Value Objects esenciales como [TenantId](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/tenants/value_objects/tenant_id.py) e [IdempotencyKey](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/conversations/value_objects/idempotency_key.py) requerían instanciación directa sin factorías semánticas (`from_raw()`, `create()`).
   - Existía duplicación de código: [CheckpointId](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/agents/value_objects/checkpoint_id.py) estaba declarado de forma idéntica y simultánea en `workflow_id.py` y en `checkpoint_id.py`.
3. **Encapsulamiento Parcial en Entidades:**
   - Agregados como `ToolApprovalRequest`, `SecurityIncident` y `WorkflowInstance` exponían atributos mutables como campos públicos en lugar de protegerlos (`_status`, `_resolved_at`, `_operator_id`) con propiedades de solo lectura (`@property`) y mutación exclusiva mediante métodos de negocio.

---

## 2. Decisión de Diseño

Se adopta una estandarización integral de la Capa de Dominio regida por los principios de **Clean Architecture**, **DDD Táctico** y **cero dependencias externas**:

### 2.1. Jerarquía Unificada de Excepciones de Dominio

- [x] **Núcleo Compartido ([src/domain/shared/exceptions.py](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/shared/exceptions.py)):**
  - Se define la jerarquía base:
    - `DomainError(Exception)` con alias `DomainException = DomainError`.
    - `DomainValidationError(DomainError, ValueError)`: Para errores estructurales de formato e invariantes de tipos primitivos.
    - `EntityNotFoundError(DomainError)`: Para agregados o entidades inexistentes.
    - `InvariantViolationError(DomainError)`: Para violaciones de consistencia de agregados.
  - Se preserva `src/domain/shared/domain_error.py` re-exportando `DomainError` para garantizar 100% de compatibilidad con código existente.

- [x] **Estrategia de Retrocompatibilidad (Dual-Inheritance):**
  - Para evitar romper capturas de excepciones en handlers o tests preexistentes (`except ValueError:`), las excepciones de validación y cálculo monetario heredan concurrentemente de `DomainError` y `ValueError`:
    ```python
    class InsufficientBudgetError(DomainError, ValueError): ...
    class TenantSuspendedError(DomainError, ValueError): ...
    class ModelNotAllowedError(DomainError, ValueError): ...
    class InvalidApprovalStateError(DomainError, ValueError): ...
    ```

- [x] **Excepciones Semánticas por Bounded Context:**
  - **Tenants ([src/domain/tenants/exceptions.py](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/tenants/exceptions.py)):** `TenantNotFoundError`, `TenantAlreadyExistsError`, `TenantSuspendedError`, `InsufficientBudgetError`, `InvalidBudgetOperationError`, `TenantValidationError`, `ModelNotAllowedError`.
  - **Conversaciones ([src/domain/conversations/exceptions.py](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/conversations/exceptions.py)):** `ConversationNotFoundError`, `InvalidConversationTitleError`, `ConsecutiveUserMessageError`, `ConsecutiveAssistantMessageError`, `MessageValidationError`.
  - **Conocimiento ([src/domain/knowledge/exceptions.py](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/knowledge/exceptions.py)):** `DocumentNotFoundError`, `DocumentValidationError`, `InvalidDocumentChunkError`.
  - **Herramientas ([src/domain/tools/exceptions.py](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/src/domain/tools/exceptions.py)):** `ToolNotFoundError`, `ToolExecutionError`, `InvalidApprovalStateError`.

### 2.2. Value Objects Inmutables y Métodos Factoría

- [x] **Inmutabilidad Garantizada:** Todos los Value Objects aplican `@dataclass(frozen=True)` o heredan de `StrEnum`.
- [x] **Métodos Factoría Semánticos:**
  - `TenantId.from_raw(raw: str)` y `TenantId.create(slug: str)`.
  - `MonetaryBudget.zero(currency: str = "USD")` y `MonetaryBudget.create(...)`.
  - `IdempotencyKey.from_raw(raw: str)` y `IdempotencyKey.create(key: str)`.
  - `WorkflowId.from_raw(raw: str)`, `WorkflowId.create(value: str)`.
  - `CheckpointId.from_raw(raw: str)`, `CheckpointId.create(value: str)`.
- [x] **Deduplicación:** Se eliminó la declaración duplicada de `CheckpointId` en `workflow_id.py`, consolidándola en `checkpoint_id.py` y re-exportándola en `workflow_id.py` por retrocompatibilidad.

### 2.3. Encapsulamiento Estricto de Entidades

- [x] **Protección de Estado Interno:**
  - `ToolApprovalRequest`: Atributos privados `_id`, `_tenant_id`, `_status`, `_operator_id`, `_justification`, etc., con `@property` públicas de solo lectura. Mutación restringida a `approve()` y `reject()`.
  - `SecurityIncident`: Atributos protegidos `_id`, `_severity`, `_rule_name`, `_prompt_preview`, `_details`, etc., expuestos como `@property`.
  - `WorkflowInstance`: Atributos protegidos `_id`, `_current_node`, `_status`, `_state_data`, etc. Incorporación de métodos de negocio `resume()` y `update_state()`.
  - `Document`: Atributos protegidos `_id`, `_status`, `_total_chunks`, etc., con transición validada mediante `mark_processing()`, `mark_indexed()`, `mark_failed()`.

---

## 3. Consecuencias y Mitigaciones

| Beneficio / Impacto | Mitigación Implementada |
| :--- | :--- |
| **Mayor Claridad Diagnóstica:** Errores específicos en lugar de `ValueError` genérico. | La herencia de `ValueError` asegura que ningún test o handler existente falle por no capturar la excepción. |
| **Cero Regresiones de Código:** Cambios transparentes en firmas de inicialización. | Se mantuvieron los parámetros y getters existentes mediante propiedades `@property`. |
| **Alineación con Clean Architecture:** Dominio puramente expresivo, agnóstico al framework y 100% tipado. | Verificación en Pyright con 0 errores y Bandit con 0 alertas de seguridad. |

---

## 4. Verificación y Calidad

- **Tests Automatizados:** 632 pruebas ejecutadas y aprobadas (100% verde) en `make test`.
- **Análisis Estático (Pyright):** 0 errores, 0 advertencias.
- **Formateo y Linter (Ruff):** 449 archivos formateados y validados, 0 infracciones.
- **SAST (Bandit):** 0 vulnerabilidades identificadas sobre 12.258 líneas de código.
