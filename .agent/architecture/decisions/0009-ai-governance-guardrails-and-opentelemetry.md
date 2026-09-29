# ADR 0009: Gobernanza de IA Empresarial, Guardrails en Tiempo Real y Observabilidad Distribuida con OpenTelemetry

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-29
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 10 — Enterprise AI Governance, Real-Time Guardrails & Distributed Observability

---

## 1. Contexto y Problemática

Con la evolución de la plataforma hacia capacidades avanzadas de orquestación multi-agente (Slice 9), ejecución de herramientas con HITL (Slice 8) y RAG híbrido (Slice 7), el sistema procesa volúmenes crecientes de prompts complejos y maneja información corporativa sensible. En este contexto, operar modelos de lenguaje en entornos empresariales exige mitigar tres riesgos críticos:

1. **Vulnerabilidades de Prompt Injection y Jailbreak:** Usuarios o atacantes pueden intentar eludir las instrucciones del sistema (*system prompt override*, exfiltración de API keys, escalamiento de privilegios o ejecución de comandos maliciosos). Si un ataque de inyección llega al backend LLM, consume cuota de tokens y expone información confidencial. Se requiere una barrera preventiva que neutralice el ataque antes de invocar el motor de inferencia.
2. **Fuga de Información Personalmente Identificable (PII):** Los usuarios envían números de tarjetas de crédito, números de seguridad social (SSN), DNI, emails y claves de API. La persistencia o envío de estos datos a proveedores externos sin anonimización previa viola normativas como GDPR, PCI-DSS y HIPAA.
3. **Sobrecarga de Latencia por Frameworks ML Pesados (Zero-Bloat Rule):** Incorporar librerías pesadas como spaCy, Presidio o modelos de embedding dedicados para guardrails introduce sobrecargas de 200–500ms y cientos de megabytes de dependencias. Para cargas de trabajo en tiempo real, los guardrails deben ejecutarse en menos de **10ms** usando Python puro, expresiones regulares precompiladas y algoritmos deterministas (como el algoritmo de Luhn para tarjetas de crédito).
4. **Falta de Trazabilidad Distribuida Extremo a Extremo:** En una arquitectura distribuida (FastAPI ➔ RabbitMQ ➔ Workers de Inferencia ➔ SQL Server), resulta inviable correlacionar errores, cuellos de botella o incidentes de seguridad sin un identificador de contexto unificado. Se requiere el estándar W3C Trace Context propagado en cabeceras HTTP y metadatos AMQP.
5. **Auditoría Forense Inmutable Multi-Tenant:** Cualquier intento de violación de políticas o inyección de prompt debe quedar registrado de forma transaccional e inmutable en Microsoft SQL Server 2022, segregado por `tenant_id` y consultable mediante APIs administrativas.

---

## 2. Decisión de Diseño

Se adopta una solución integral basada en Clean Architecture, DDD, CQRS, W3C Trace Context y ejecución concurrente con AnyIO, garantizando estricta segregación de responsabilidades:

### 2.1. Dominio y Contratos (DDD)

1. **Value Objects (`src/domain/governance/value_objects/`):**
   - `SafetyVerdict`: Veredicto inmutable (`is_safe`, `violation_type`, `risk_score`, `matched_rule`, `details`). Métodos de factoría `safe()` y `violation()`.
   - `IncidentSeverity`: Enum jerárquico (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
   - `PiiEntityMatch`: Captura la entidad detectada, índices de inicio/fin, valor enmascarado y fragmento original para trazabilidad.
   - `TraceContext`: Contexto W3C inmutable (`trace_id`, `span_id`, `trace_flags`, `tracestate`). Factoría `from_traceparent()` y `to_traceparent()`.
2. **Agregado Raíz (`src/domain/governance/entities/security_incident.py`):**
   - `SecurityIncident`: Administra la identidad del incidente, severidad, regla violada, previsualización del prompt y metadatos. Emite `SafetyViolationBlockedDomainEvent` y, para severidades altas o críticas, `PromptInjectionDetectedDomainEvent`.
3. **Puertos de Dominio (Driven Ports en `src/domain/governance/ports/`):**
   - `SafetyGuardrailPort`: Evalúa texto de entrada y fragmentos de stream en tiempo real.
   - `PiiScannerPort`: Detecta y enmascara PII de manera síncrona/asíncrona.
   - `IncidentRepositoryPort`: Almacena incidentes, lista con filtros paginados y calcula métricas agregadas por tenant.
4. **Excepciones de Dominio:**
   - `SafetyPolicyViolationError`: Excepción específica cuando una política de seguridad bloquea una solicitud.

---

### 2.2. Capa de Aplicación (CQRS & Pipeline de Seguridad)

1. **Pipeline Concurrente (`SafetyGuardrailPipelineService`):**
   - Orquesta concurrentemente la verificación de seguridad heurística y el escaneo/enmascaramiento de PII utilizando `anyio.create_task_group()`.
   - Devuelve `GuardrailPipelineResult` conteniendo el texto sanitizado y el veredicto de seguridad consolidado.
2. **Ejecutor Protegido (`GuardedCommandExecutor`):**
   - Envuelve la ejecución de comandos de aplicación (`SendMessageCommand`, etc.), evaluando el texto a través del pipeline de guardrails.
   - Si se detecta una violación, persiste un `SecurityIncident` de forma transaccional mediante `IncidentRepositoryPort` y eleva `SafetyPolicyViolationError` sin invocar el LLM ni publicar en RabbitMQ.
3. **Portador de Contexto de Rastreo (`TraceContextCarrier`):**
   - Serializa y deserializa el W3C `traceparent` hacia/desde cabeceras HTTP (`traceparent`, `x-trace-id`, `x-span-id`) y diccionarios de metadatos de mensajería AMQP en RabbitMQ.
4. **Comandos y Consultas CQRS:**
   - `RecordSecurityIncidentCommand` / `RecordSecurityIncidentHandler`.
   - `ListIncidentsQuery` / `ListIncidentsQueryHandler`.
   - `GetGovernanceMetricsQuery` / `GetGovernanceMetricsQueryHandler`.

---

### 2.3. Infraestructura de Guardrails y Persistencia

1. **Escáner Regex de PII con Validación Luhn (`RegexPiiScannerAdapter`):**
   - Implementa expresiones regulares precompiladas para emails, teléfonos, SSN, API keys y tarjetas de crédito.
   - Valida tarjetas de crédito mediante el **algoritmo de Luhn** para eliminar falsos positivos de secuencias numéricas aleatorias.
   - Resuelve solapamientos de patrones ordenando por posición inicial y longitud.
   - Tiempo de ejecución verificado: **< 1ms**, cumpliendo holgadamente el límite de 10ms.
2. **Detector Heurístico de Inyección (`HeuristicInjectionDetectorAdapter`):**
   - Reglas precompiladas contra patrones de escape, jailbreaks comunes (*DAN*, *AIM*, *developer mode*), overrides de system prompt e intentos de extracción de claves.
3. **Filtro de Guardrails para Streaming (`AnyioStreamGuardrailFilter`):**
   - Intercepta fragmentos emitidos en Server-Sent Events (SSE) y evalúa el contenido en una ventana deslizante configurable. Si el LLM emite contenido prohibido, corta el stream elevando `SafetyPolicyViolationError`.
4. **Persistencia Transaccional en MSSQL 2022 (`MssqlIncidentRepository`):**
   - Modelo relacional `SecurityIncidentModel` mapeado a la tabla `security_incidents` con índices compuestos por `tenant_id` y `created_at`.
   - Soporte para consultas paginadas con filtrado dinámico (`severity`, `rule_name`, rangos de fechas).
   - Migración Alembic `0007_governance_incidents.py`.
5. **Aislamiento Estricto de OpenTelemetry (`src/infrastructure/telemetry/`):**
   - Las dependencias del SDK de OpenTelemetry (`opentelemetry-api`, `opentelemetry-sdk`) se encapsulan exclusivamente en adaptadores de infraestructura (`OpenTelemetryTracingAdapter`). El dominio y la aplicación desconocen la existencia del SDK de OTel, comunicándose a través de abstracciones y `TraceContext`.

---

### 2.4. Interfaces HTTP & Middleware

1. **Middleware de OpenTelemetry (`OpenTelemetryMiddleware`):**
   - Extrae el W3C `traceparent` de las peticiones entrantes o genera un nuevo span raíz.
   - Inyecta cabeceras `X-Trace-ID` y `X-Span-ID` en todas las respuestas HTTP para permitir correlación directa desde el cliente.
2. **Manejador Centralizado de Excepciones:**
   - Captura `SafetyPolicyViolationError` en FastAPI y retorna `HTTP 400 Bad Request` estructurado con el código de violación, regla disparada y score de riesgo, sin revelar detalles internos del sistema.
3. **API Administrativa de Gobernanza (`GovernanceRouter`):**
   - `GET /admin/tenants/{tenant_id}/incidents`: Lista incidentes auditables del tenant con paginación y filtros.
   - `GET /admin/governance/metrics`: Retorna métricas globales (total de incidentes, distribución por severidad y desglose por regla).

---

## 3. Consecuencias y Criterios de Aceptación

### Positivas

- **Latencia Mínima (<10ms):** El pipeline de guardrails añade menos de 1ms de sobrecarga por petición, asegurando que las peticiones limpias fluyan sin penalización de rendimiento.
- **Ahorro de Costos:** Las peticiones maliciosas son rechazadas antes de invocar el LLM, protegiendo el presupuesto de tokens y la capacidad de inferencia.
- **Privacidad Garantizada:** Los datos sensibles son anonimizados antes de la persistencia en base de datos o el envío al broker de mensajería.
- **Trazabilidad de Grado Empresarial:** Correlación unificada extremo a extremo a través de W3C Trace Context en logs, métricas y spans.
- **Cumplimiento Normativo:** Registro inmutable de incidentes de seguridad para auditorías SOX, PCI-DSS e ISO 27001.

### Trade-offs

- Las heurísticas regex requieren mantenimiento y actualización continua de firmas ante nuevas técnicas de jailbreak adversarias (compensado por la extensibilidad del puerto `SafetyGuardrailPort` para incorporar modelos clasificadores especializados en el futuro sin romper el dominio).
