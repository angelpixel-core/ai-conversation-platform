# ADR 0003: Desacoplamiento de Inferencia LLM mediante RabbitMQ y Proceso Worker Autónomo

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-27
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 4 — Decoupled Event Broker Worker (RabbitMQ / Redis PubSub)

---

## 1. Contexto y Problemática

En las fases iniciales de la plataforma (Slices 1 a 3), la inferencia con Modelos de Lenguaje Grande (LLMs) y la persistencia de mensajes se coordinaban dentro del flujo de la API web o mediante sondeos síncronos:

- Las llamadas a LLMs externos implican latencias variables y significativas (de 500 ms a más de 30 segundos por turno), además de estar sujetas a límites de tasa (*rate limits*) o indisponibilidades transitorias de red.
- Ejecutar la inferencia o esperar respuestas síncronas bloquea los workers ASGI del proceso HTTP web (`chatbot_api`), degradando drásticamente el *throughput*, la concurrencia y la resiliencia global del servicio ante aumentos de carga.
- Se requería una arquitectura completamente asíncrona, orientada a eventos y desacoplada, con garantías transaccionales (*At-Least-Once Delivery* y *Zero Message Loss*) y resiliencia ante caídas de la API o del Worker.

---

## 2. Decisión de Diseño

Se adopta un desacoplamiento estricto a nivel de proceso y de transporte de mensajería basado en **AMQP 0-9-1 (RabbitMQ)**, el **Patrón Transactional Outbox**, y **Concurrencia Estructurada (`anyio`)**:

### 2.1. Arquitectura de Procesos Separados (Productor / Consumidor)

1. **Servicio API (`chatbot_api` / `src.main:app`):**
   - Ingesta de mensajes de usuario vía endpoint `POST /conversations/{id}/messages`.
   - Modifica el agregado `Conversation`, registra el `MessageAppendedDomainEvent` y auto-drena los eventos en el repositorio persistiendo tanto el agregado como el registro en `outbox_messages` dentro de una **única transacción ACID** en Microsoft SQL Server 2022.
   - Retorna respuesta inmediata al cliente HTTP (<50ms).
2. **Relay Transaccional (`OutboxRelayService`):**
   - Extrae eventos con estado `pending` mediante bloqueos de fila no bloqueantes en SQL Server (`WITH (UPDLOCK, READPAST)`).
   - Publica los eventos en el exchange de RabbitMQ (`conversation.events`) y actualiza el estado a `published`.
3. **Servicio Worker Autónomo (`chatbot_worker` / `src.worker:main`):**
   - Proceso independiente orquestado por `WorkerContainer`.
   - Consume mensajes de la cola `conversation.llm_processing.queue` a través del adaptador `RabbitMQConsumerAdapter`.
   - Ejecuta el caso de uso `LlmMessageProcessingWorker`, consulta el contexto de la conversación, invoca el puerto `LlmClientPort` y persiste la respuesta del asistente mediante `AppendAssistantMessageHandler` dentro de su propio `MssqlUnitOfWork`.
   - Emite confirmaciones explícitas de mensajería (`ack()` / `nack()`).

### 2.2. Topología RabbitMQ y Resiliencia con Dead Letter Queue (DLQ)

- **Exchange Principal:** `conversation.events` (Tipo: `topic`, Durable).
- **Cola de Procesamiento:** `conversation.llm_processing.queue` (Durable), vinculada con routing key `conversation.message.appended`.
- **Dead Letter Exchange (DLX):** `conversation.dlx` (Tipo: `topic`, Durable).
- **Dead Letter Queue (DLQ):** `conversation.llm_processing.dlq` (Durable).
- **Política ante Fallos:** Errores transitorios o no recuperables provocan rechazo con `requeue=False`, enrutando el mensaje automáticamente al DLQ mediante los argumentos `x-dead-letter-exchange` y `x-dead-letter-routing-key` para auditoría y reintento diferido sin pérdida de información.

### 2.3. Concurrencia Estructurada y Ciclo de Vida

- Toda la ejecución asíncrona y de background utiliza la biblioteca agnóstica `anyio`.
- El proceso worker captura señales POSIX (`SIGINT`, `SIGTERM`) mediante `anyio.open_signal_receiver()` y garantiza el cierre ordenado (*graceful shutdown*) de los canales AMQP, conexiones de base de datos y tareas concurrentes en curso.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Aislamiento Total de Procesos:** La caída, saturación o reinicio del servicio web no interrumpe el procesamiento del worker, y viceversa. Si el worker cae, los mensajes quedan retenidos de forma segura en las colas durables de RabbitMQ.
- **Escalabilidad Horizontal:** Se pueden desplegar múltiples réplicas del contenedor `worker` compitiendo por la misma cola para balancear la carga de inferencia LLM sin alterar la capa web ni generar condiciones de carrera.
- **Tolerancia a Fallos y Auditoría:** Los eventos envenenados o caídas reiteradas de la API del LLM se aíslan en la DLQ con trazabilidad total sin bloquear la cola principal.
- **Cumplimiento de Clean Architecture:** La capa de aplicación (`LlmMessageProcessingWorker`) interactúa exclusivamente con puertos abstractos (`EventConsumerPort`, `LlmClientPort`, `UnitOfWork`); la infraestructura concreta de RabbitMQ (`aio-pika`) y SQL Server permanece encapsulada en adaptadores.

### Negativas / Mitigaciones

- **Complejidad Operacional:** Requiere orquestar instancias de RabbitMQ y SQL Server junto con múltiples procesos de aplicación. *Mitigación:* Se implementa configuración declarativa en `docker-compose.yml` y comandos de ciclo de vida unificados en el `Makefile` (`make stack/up`, `make run-worker`, `make run-api`).
