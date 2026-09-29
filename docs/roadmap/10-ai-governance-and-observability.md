# Roadmap de Implementación — Slice 10: Enterprise AI Governance, Real-Time Guardrails & Distributed Observability

Este documento detalla la ruta de desarrollo para gobernanza de modelos de lenguaje, mitigación activa de riesgos (*Guardrails / Jailbreak / Prompt Injection*), anonimización de datos sensibles (*PII Masking & Redaction*), observabilidad distribuida con **OpenTelemetry (OTel / W3C TraceContext)** y registro de auditoría forense inmutable sobre **Microsoft SQL Server 2022 (MSSQL)**, **AnyIO Structured Concurrency** y **RabbitMQ**.

---

## 🎯 Objetivo del Slice 10

Cerrar el ciclo de vida del software con blindaje operativo, seguridad defensiva en profundidad y observabilidad de grado enterprise:

1. **Real-Time Safety Guardrails (Input & Output Interceptors):** Detección e intercepción temprana de intentos de inyección de prompt (*jailbreak*, *system prompt leak*, *instruction overrides*), toxicidad o peticiones fuera de política antes de que alcancen al proveedor LLM o lleguen al usuario final.
2. **PII Masking & Token Anonymization (Zero-Bloat Pattern Engine):** Redacción y anonimización automática de información personal identificable (tarjetas de crédito validadas con algoritmo de Luhn, DNI/SSN, correos electrónicos, teléfonos, tokens/claves API) en memoria antes de persistir en MSSQL o despachar al broker de mensajería.
3. **Distributed Tracing con OpenTelemetry & W3C TraceContext:** Trazabilidad distribuida extremo a extremo con inyección y propagación de contexto W3C (`traceparent`, `tracestate`, `trace_id`, `span_id`) a través de requests HTTP, mensajes en colas RabbitMQ y tareas asíncronas en workers con AnyIO.
4. **Métricas de Gobernanza y Auditoría Forense en MSSQL:** Registro transaccional inmutable en SQL Server de cada violación de política de seguridad, prompt bloqueado y cálculo de latencia de guardrail vs. latencia de inferencia, sin fugas de datos confidenciales.
5. **Sinergia con Slices Previos:**
   - **Slice 6 (Multi-Tenancy & Budgets):** Todo incidente y métrica queda estrictamente segregado por `tenant_id`. Los prompts bloqueados por guardrail abortan inmediatamente el flujo, evitando deducción o consumo innecesario de cuota monetaria.
   - **Slice 7 (Hybrid RAG):** El scanner de PII y filtro de seguridad opera sobre los textos ingresados antes de indexar o recuperar fragmentos de conocimiento.
   - **Slice 8 (HITL & Sandboxed Tools):** Las herramientas de alta criticidad ejecutan sus validaciones de seguridad bajo el mismo contexto de traza distribuida.
   - **Slice 9 (Multi-Agent State Graphs):** El `TraceContext` se propaga de forma transparente entre subagentes paralelos y se guarda en los checkpoints de estado.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente HTTP ]
       │  (1. Request con Header 'traceparent' / W3C TraceContext)
       ▼
[ OTel Tracing Middleware + Tenant Context Middleware ]
       │  (2. Extrae o inicia Root Span: 'http.request.conversation')
       │  (Inyecta X-Trace-ID y X-Span-ID en contexto y respuesta)
       ▼
[ Input Guardrails Interceptor (AnyIO TaskGroup) ]
       ├── Heuristic Prompt Injection Detector (Jailbreak / System Override)
       └── Regex & Luhn PII Scanner (Tarjetas, DNI, Emails, Secrets)
       │
       ├─── Violación Crítica de Política ────────────────┐
       │                                                  ▼
       │      [ Registra SecurityIncident en MSSQL: severity='HIGH'/'CRITICAL' ]
       │      [ Corta el flujo de inmediato: HTTP 400 'SafetyPolicyViolationError' ]
       │
       ▼ (Aprobado / Sanitizado con PII Redactada)
[ Application Layer: Command Handlers (SendMessageCommand) ]
       │  (3. Propaga W3C TraceContext en Message Envelope / Headers a RabbitMQ)
       ▼
[ RabbitMQ Topic Broker ('conversation.events') ]
       │  (4. Worker extrae TraceContext y crea Child Span: 'worker.llm.inference')
       ▼
[ LLM Stream Worker Process ]
       │  (5. Tokens generados pasan por Output Guardrail Filter en vuelo)
       ▼
[ Output Guardrail Buffer (AnyIO Stream Filter) ]
       │  (6. Verifica alucinaciones de PII o respuestas prohibidas en tiempo real)
       ▼
[ Cliente HTTP (Recibe tokens limpios, seguros y auditados vía SSE) ]
```

---

## 🛠️ Tecnologías y Reglas de Diseño

Para preservar la pureza de la arquitectura hexagonal y evitar sobrecarga o inestabilidad operativa, se establecen las siguientes directivas tecnológicas:

1. **Zero-Bloat para Guardrails:** Queda descartado el uso de modelos locales pesados (como Spacy, Transformers o Presidio) en la capa de runtime, que elevarían el footprint de memoria en cientos de megabytes. Se implementa un motor nativo y ultra-rápido en Python puro basado en expresiones regulares optimizadas precompiladas, validación de Luhn para números de tarjeta de crédito y detección heurística de patrones de inyección de prompt (<10ms de latencia).
2. **OpenTelemetry Limpio:** El Dominio y la Aplicación permanecen 100% agnósticos a SDKs externos de telemetría mediante los value objects `TraceContext` y el puerto/carrier `TraceContextCarrier`. La instrumentación física se aísla en `src/infrastructure/telemetry/` y middlewares HTTP.
3. **Persistencia Unificada en MSSQL 2022:** Los modelos relacionales se integran en `src/infrastructure/persistence/mssql/models.py` (`SecurityIncidentModel` y `PiiAuditLogModel`) con índices compuestos multi-tenant `(tenant_id, id)` y `(tenant_id, created_at)`.
4. **Concurrencia Estructurada:** Todo procesamiento paralelo de evaluadores de seguridad y filtrado de flujos se realiza mediante `anyio.create_task_group()` y generadores asíncronos limpios sin corrutinas huérfanas.

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio y Contratos de Gobernanza y Seguridad

*Entidades de incidentes, políticas de seguridad, value objects de PII y trazabilidad.*

- [x] **Value Objects de Seguridad, PII y Trazabilidad**
  - Archivo: `src/domain/governance/value_objects/safety_verdict.py` (`is_safe`, `violation_type`, `risk_score`, `matched_rule`, `details`).
  - Archivo: `src/domain/governance/value_objects/pii_entity_match.py` (`entity_type`, `start_idx`, `end_idx`, `masked_value`, `original_preview`).
  - Archivo: `src/domain/governance/value_objects/trace_context.py` (W3C standard `trace_id`, `span_id`, `parent_span_id`, `trace_flags`, `tracestate`).
  - Archivo: `src/domain/governance/value_objects/incident_severity.py` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

- [x] **Entidad de Dominio: SecurityIncident (Aggregate Root)**
  - Archivo: `src/domain/governance/entities/security_incident.py`
  - Invariantes de ciclo de vida: creación inmutable, registro de severidad, regla violada, tenant scoping y publicación de eventos de dominio.

- [x] **Eventos de Dominio de Gobernanza**
  - Archivo: `src/domain/governance/events/governance_events.py`
  - Eventos: `PromptInjectionDetectedDomainEvent`, `PiiRedactionAppliedDomainEvent`, `SafetyViolationBlockedDomainEvent`.

- [x] **Puertos de Seguridad y Repositorio Forense (Driven Ports)**
  - Archivo: `src/domain/governance/ports/safety_guardrail_port.py` (`evaluate_input`, `evaluate_output_chunk`).
  - Archivo: `src/domain/governance/ports/pii_scanner_port.py` (`scan_and_mask_pii`).
  - Archivo: `src/domain/governance/ports/incident_repository_port.py` (`save_incident`, `get_incident`, `list_incidents_by_tenant`, `get_metrics`).

- [x] **Excepciones de Dominio**
  - Archivo: `src/domain/governance/exceptions.py` (`SafetyPolicyViolationError`, `PiiMaskingError`, `IncidentNotFoundError`).

- [x] **Tests Unitarios de Dominio (100% Verde)**
  - Archivo: `tests/unit/domain/governance/test_safety_verdict.py`
  - Archivo: `tests/unit/domain/governance/test_pii_entity_match.py`
  - Archivo: `tests/unit/domain/governance/test_trace_context.py`
  - Archivo: `tests/unit/domain/governance/test_security_incident.py`

---

### Fase 2: Capa de Aplicación (Guardrail Pipelines & Telemetría OTel)

*Intercepción desacoplada mediante AnyIO TaskGroups, decoradores y comandos CQRS.*

- [x] **Servicio de Aplicación: Safety Guardrail Pipeline**
  - Archivo: `src/application/governance/services/guardrail_pipeline_service.py`
  - Ejecuta validaciones concurrentes con `anyio.create_task_group()` (detección de inyección, escaneo de PII y evaluación de políticas de seguridad).

- [x] **Interceptor / Decorador Guardrail en Comandos**
  - Archivo: `src/application/shared/governance/guarded_command_executor.py`
  - Intercepta comandos (ej. `SendMessageCommand`), ejecuta el pipeline de guardrails, redacta PII y bloquea infracciones críticas registrando incidentes de forma automática.

- [x] **Portador de Contexto de Trazas (OTel / W3C Trace Propagator)**
  - Archivo: `src/application/shared/telemetry/trace_context_carrier.py`
  - Serializa y deserializa encabezados W3C (`traceparent`, `tracestate`) para inyección transparente en eventos de dominio y mensajes de RabbitMQ.

- [x] **Comandos y Queries CQRS de Gobernanza**
  - Archivo: `src/application/governance/commands/record_incident.py` (`RecordSecurityIncidentCommand`, `RecordSecurityIncidentHandler`).
  - Archivo: `src/application/governance/queries/list_incidents.py` (`ListIncidentsQuery`, `ListIncidentsQueryHandler`).
  - Archivo: `src/application/governance/queries/get_governance_metrics.py` (`GetGovernanceMetricsQuery`, `GetGovernanceMetricsQueryHandler`).

- [x] **Tests Unitarios de Aplicación**
  - Archivo: `tests/unit/application/governance/test_guardrail_pipeline_service.py`
  - Archivo: `tests/unit/application/governance/test_guarded_command_executor.py`
  - Archivo: `tests/unit/application/governance/test_trace_context_carrier.py`
  - Archivo: `tests/unit/application/governance/test_record_incident_handler.py`

---

### Fase 3: Infraestructura MSSQL (Auditoría Forense & Logs Inmutables)

*Tablas optimizadas en SQL Server 2022 para trazabilidad de seguridad y cumplimiento legal.*

- [x] **Modelos ORM Físicos en MSSQL (`models.py`)**
  - Archivo: `src/infrastructure/persistence/mssql/models.py`
  - Añade `SecurityIncidentModel` (`security_incidents` table) con índices `(tenant_id, id)` y `(tenant_id, created_at)`.
  - Añade `PiiAuditLogModel` (`pii_audit_logs` table) con hash SHA-256 de texto original y texto redactado.

- [x] **Mapper de Persistencia Relacional**
  - Archivo: `src/infrastructure/persistence/mssql/governance_mapper.py`
  - Mapeo bidireccional entre `SecurityIncident` y `SecurityIncidentModel`.

- [x] **Adaptadores de Repositorio de Incidentes (MSSQL e In-Memory)**
  - Archivo: `src/infrastructure/persistence/mssql/mssql_incident_repository.py`
  - Escrituras atómicas con aislamiento de sesión independiente para garantizar persistencia incluso ante rollback del flujo principal.
  - Archivo: `src/infrastructure/persistence/in_memory/in_memory_incident_repository.py` (para tests rápidos en memoria).

- [x] **Migración de Base de Datos Alembic**
  - Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0007_governance_and_security_audit.py`

- [x] **Tests de Integración con SQL Server (Testcontainers / MSSQL)**
  - Archivo: `tests/unit/infrastructure/persistence/test_in_memory_incident_repository.py`
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_incident_repository.py`

---

### Fase 4: Infraestructura de Guardrails y OpenTelemetry Adapters

*Implementación física de analizadores de seguridad de alta velocidad y exportadores OTel.*

- [x] **Adaptadores de Guardrails (Pattern + Luhn + Heuristic Detector)**
  - Archivo: `src/infrastructure/governance/regex_pii_scanner_adapter.py` (Luhn algorithm para tarjetas, patrones regex para DNI/SSN, emails, teléfonos y API keys).
  - Archivo: `src/infrastructure/governance/heuristic_injection_detector_adapter.py` (detección de patrones DAN, jailbreak prompts, tags de evasión y system instructions override).

- [x] **Configuración e Inicialización de OpenTelemetry**
  - Archivo: `src/infrastructure/telemetry/opentelemetry_config.py`
  - Inicialización limpia de TracerProvider con W3C Propagator y fallback resiliente en ausencia de colector externo.

- [x] **Filtro de Output Stream en AnyIO**
  - Archivo: `src/infrastructure/governance/anyio_stream_guardrail_filter.py`
  - Inspección con ventana deslizante sobre generadores asíncronos de tokens para interceptar en vuelo respuestas del modelo que violen políticas.

- [x] **Propagación en RabbitMQ y Worker**
  - Integración de `TraceContextCarrier` en `src/infrastructure/messaging/rabbitmq/` para inyectar headers AMQP `x-trace-id`, `x-span-id` y procesar en `worker_handler.py`.

- [x] **Tests de Integración de Guardrails & Tracing**
  - Archivo: `tests/unit/infrastructure/governance/test_regex_pii_scanner.py`
  - Archivo: `tests/unit/infrastructure/governance/test_heuristic_injection_detector.py`
  - Archivo: `tests/unit/infrastructure/governance/test_anyio_stream_guardrail_filter.py`
  - Archivo: `tests/unit/infrastructure/telemetry/test_opentelemetry_tracing.py`

---

### Fase 5: Interfaces HTTP & Headers de Seguridad

*Respuestas de infracción, códigos de política, routers y headers de rastreo.*

- [x] **Middleware Global de OpenTelemetry & Trace Injection**
  - Archivo: `src/interfaces/http/middlewares/opentelemetry_middleware.py` (inyecta `trace_id` y `span_id` en headers de respuesta `X-Trace-ID` y `X-Span-ID`).

- [x] **Manejo Centralizado de Excepciones de Seguridad**
  - Registro en `src/interfaces/http/api.py` para mapear `SafetyPolicyViolationError` a `HTTP 400 Bad Request` estructurado.

- [x] **Schemas y Router de Auditoría de Gobernanza (Admin API)**
  - Archivo: `src/interfaces/http/governance_schemas.py` (`IncidentResponse`, `GovernanceMetricsResponse`, `IncidentFilterParams`).
  - Archivo: `src/interfaces/http/routers/governance_router.py`
    - `GET /admin/tenants/{tenant_id}/incidents` (`HTTP 200 OK`).
    - `GET /admin/governance/metrics` (`HTTP 200 OK`).

- [x] **Tests de Integración HTTP / E2E**
  - Archivo: `tests/integration/api/test_prompt_injection_blocked.py`
  - Archivo: `tests/integration/api/test_pii_redacted_response.py`
  - Archivo: `tests/integration/api/test_governance_admin_endpoints.py`
  - Archivo: `tests/integration/api/test_opentelemetry_headers.py`


---

### Fase 6: Ensamble, Container, Plantillas y Documentación

- [x] **Actualización de `src/container.py` y `src/worker_container.py`**
  - Inyección de dependencias para `SafetyGuardrailPort`, `PiiScannerPort`, `IncidentRepositoryPort`, `GuardrailPipelineService` y configuración OTel.

- [x] **Extracción de Plantillas Canónicas (`.agent/templates/`)**
  - `domain/value_objects/safety_verdict.tt.py`
  - `domain/entities/security_incident.tt.py`
  - `application/services/guardrail_pipeline_service.tt.py`
  - `application/shared/trace_context_carrier.tt.py`
  - `infrastructure/governance/regex_pii_scanner.tt.py`
  - `infrastructure/governance/anyio_stream_guardrail_filter.tt.py`
  - `tests/test_guardrail_pipeline.tt.py`

- [x] **Documento de Decisión Arquitectónica (ADR 0009)**
  - Archivo: `.agent/architecture/decisions/0009-ai-governance-guardrails-and-opentelemetry.md`.

- [x] **Actualización del Diagrama Vivo (`system-map.mermaid.md`)**
  - Incorporación de nodos y relaciones para la capa de Guardrails, colector OTel y auditoría forense en MSSQL.

- [x] **Generación de Documentación y OpenAPI**
  - Ejecución de `make docs-build` para regenerar `public/openapi.json` y `public/index.html` (ReDoc).

---

## 🔍 Criterios de Aceptación del Slice 10

1. **Bloqueo Preventivo Eficaz:** Un ataque de inyección de prompt o jailbreak conocido es neutralizado en menos de 10ms por el pipeline de guardrails, retornando un error explicativo `HTTP 400 SafetyPolicyViolationError` sin consumir tokens del LLM de backend.
2. **Anonimización Cero-Fuga:** Cualquier dato sensible (tarjetas de crédito, DNI, emails, tokens) es sustituido por tokens de máscara (ej. `[REDACTED_CREDIT_CARD]`) antes de que el mensaje quede persistido en MSSQL o enviado al broker.
3. **Trazabilidad Distribuida Continua:** Una traza generada en el endpoint HTTP mantiene el mismo `TraceID` en los spans del servidor web, en el mensaje de RabbitMQ y en el procesamiento del worker de inferencia.
4. **Registro Inmutable de Seguridad:** Toda petición bloqueada genera de forma transaccional un registro auditable en SQL Server con la regla violada, severidad y timestamp, garantizando el cumplimiento normativo.
5. **Calidad de Código y Calidad de Integración:** Suite completa con 100% verde en `pytest`, 0 errores en `ruff check`, 0 errores en `pyright`, y CI disparado en pushes a ramas `feat/**`.
