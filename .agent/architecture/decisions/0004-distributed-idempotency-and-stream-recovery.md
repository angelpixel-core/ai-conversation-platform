# ADR 0004: Auditoría Empresarial, Idempotencia Distribuida y Recuperación Resiliente de Streams SSE

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-27
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 5 — Enterprise Auditing, Distributed Idempotency & Resilient Stream Recovery

---

## 1. Contexto y Problemática

En un entorno conversacional distribuido con inferencia LLM en segundo plano y transporte asíncrono (RabbitMQ + FastAPI):

1. **Riesgo de Doble Ejecución e Inconsistencia:**
   - La entrega de mensajes en brokers AMQP garantiza *At-Least-Once Delivery*. En caso de reenvíos (`redelivered=True`), fallas de red entre el broker y el worker, o reintentos automáticos del cliente HTTP por *timeouts*, se producían ejecuciones redundantes de comandos (`SendMessage`, `CreateConversation`), provocando respuestas duplicadas del asistente y costos innecesarios de inferencia LLM.
2. **Fragilidad de Conexiones en Clientes SSE (Server-Sent Events):**
   - Las conexiones móviles o web sufren micro-cortes frecuentes. Si un stream SSE se desconecta a la mitad de la respuesta del LLM, el cliente tradicionalmente debía reiniciar la petición, forzando una nueva llamada al modelo, duplicando el consumo de tokens y degradando la experiencia de usuario.
3. **Ausencia de Trazabilidad y Control de Costos:**
   - No existía un registro transaccional inmutable para auditar el volumen exacto de tokens consumidos, el actor responsable y los metadatos de ejecución por conversación.

---

## 2. Decisión de Diseño

Se implementó una arquitectura integral de auditoría, deduplicación e hidratación de streams sustentada en Clean Architecture, DDD y CQRS:

### 2.1. Idempotencia Distribuida Multinivel (HTTP & AMQP)

1. **Value Object de Dominio (`IdempotencyKey`):**
   - Encapsula la validación de formato (longitud 1..128 caracteres, alfanumérico con guiones y guiones bajos).
2. **Puerto de Repositorio (`IdempotencyRepositoryPort`):**
   - Abstracción atómica para adquisición de bloqueos de ejecución (`try_acquire` con TTL) y persistencia del resultado (`COMPLETED`, `FAILED`, `PENDING`).
3. **Pipeline de Aplicación (`IdempotentCommandExecutor`):**
   - Envuelve la ejecución de comandos. Si la clave ya fue completada, retorna el resultado cacheado inmediatamente sin invocar el handler subyacente. Si la operación está en curso, levanta `IdempotencyConflictError` (mapeado a `HTTP 409 Conflict`).
4. **Dependencia HTTP FastAPI (`get_optional_idempotency_key`):**
   - Extrae e inspecciona el encabezado `Idempotency-Key` en `POST /conversations` y `POST /conversations/{id}/messages`.
5. **Deduplicación en Worker AMQP:**
   - Deduplica mensajes entrantes usando `worker:event:<envelope_id>`, evitando inferencias redundantes si RabbitMQ reenvía un evento previamente procesado.

### 2.2. Buffer Secuenciado y Recuperación Transparente de Streams SSE

1. **Value Object (`StreamChunk`):**
   - Fragmento inmutable con `sequence_number` estrictamente incremental, contenido y bandera `is_final`.
2. **Buffer de Persistencia (`StreamBufferRepositoryPort` / MSSQL / In-Memory):**
   - El Worker almacena cada chunk emitido por el LLM en tiempo real en la tabla `stream_buffer_chunks`.
3. **Servicio de Recuperación (`StreamRecoveryService` & `ResumeStreamQuery`):**
   - Consulta fragmentos con `sequence_number > since_sequence`. Si el stream sigue en progreso, sondea concurrentemente hasta recibir el fragmento final.
4. **Soporte Estándar HTTP `Last-Event-ID`:**
   - El endpoint `GET /conversations/{id}/stream` inspecciona el header estándar SSE `Last-Event-ID`. Al reconectarse, el cliente recibe únicamente los tokens no consumidos, sin re-ejecutar el LLM.

### 2.3. Auditoría Inmutable de Tokens (`AuditLogRecord` & `AuditRepositoryPort`)

1. **Entidad de Dominio Inmutable (`AuditLogRecord`):**
   - Registra `event_name`, `actor_id`, `resource_type`, `resource_id`, `action`, `tokens_consumed`, timestamp UTC y payload JSON.
2. **Persistencia Relacional en MSSQL (`audit_logs`):**
   - Registro append-only ejecutado automáticamente por el worker al finalizar cada inferencia LLM (`llm_inference_completed`).

---

## 3. Consecuencias y Beneficios

### Positivas

- **Semántica Exactly-Once Lógica:** Protege contra reintentos accidentales tanto a nivel de API HTTP como en el procesamiento asíncrono de eventos AMQP.
- **Experiencia de Usuario Continua y Económica:** Clientes con conectividad intermitente reanudan streams de forma instantánea gracias a `Last-Event-ID`, ahorrando 100% de los tokens ya generados.
- **Gobernanza y Control Financiero:** Cada token consumido por el LLM queda registrado de forma inmutable en SQL Server con trazabilidad total hacia la conversación y el evento causante.
- **Concurrencia Estructurada:** Todo el flujo de streaming, polling y reconexión opera bajo `anyio` respetando el árbol de cancelación cooperativa.
