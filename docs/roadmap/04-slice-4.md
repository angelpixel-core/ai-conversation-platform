# Roadmap de Implementación — Slice 4: Decoupled Event Broker Worker

Este documento detalla la ruta de desarrollo, desacoplamiento de procesos asíncronos mediante cola externa de mensajes, garantías de entrega (*At-least-once*) y verificación para el cuarto slice vertical de **ai-conversation-platform**.

---

## 🎯 Objetivo del Slice 4

Desacoplar completamente el ciclo de vida del servidor HTTP del procesamiento de background. En lugar de procesar los eventos de Outbox en tareas internas acopladas al proceso web, el sistema introduce:

1. **Un Broker de Mensajería Externo (RabbitMQ):** Para encolar eventos de forma resiliente con soporte de acknowledgment (`ack`/`nack`), prefetch count, reintentos y Dead-Letter Queues (DLQ).
2. **Proceso Worker Autónomo (`src/worker.py`):** Un proceso independiente dedicado exclusivamente a consumir eventos desde el broker, invocar al LLM y despachar/guardar respuestas mediante concurrencia estructurada con `anyio`.
3. **Mecanismo Outbox Relay (Transactional Polling):** Publicación segura de eventos desde Microsoft SQL Server 2022 (`outbox_messages`) hacia RabbitMQ mediante consultas atómicas con salto de bloqueos (`WITH (UPDLOCK, READPAST)` / `with_for_update(skip_locked=True)`), eliminando el problema de doble escritura (*Dual-Write Problem*).

---

## 🏗️ Desglose Arquitectónico del Flujo

```txt
[ Cliente HTTP ]
        │
        ▼
[ FastAPI (API Process) ]
        │  (1. Guarda Conversación + Outbox en SQL Server dentro de la misma transacción ACID)
        ▼
[ Microsoft SQL Server 2022 (outbox_messages table) ]
        ▲
        │  (2. Outbox Relay Poller lee eventos status='PENDING' con UPDLOCK, READPAST)
        ▼
[ Outbox Relay Service (anyio task group) ]
        │  (3. Publica mensaje al exchange 'ai_platform.events' y marca status='PUBLISHED')
        ▼
[ Event Broker (RabbitMQ) ]
        │  (4. Encola en cola duradera: 'conversation.llm_processing.queue' con DLQ asociada)
        ▼
[ Worker Process (src/worker.py via anyio) ]
        │  (5. Consume mensaje, ejecuta LLM Processing, persiste asistente vía UoW y emite ACK)
        ▼
[ LLM Gateway / External API ]
```

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio, Contratos de Aplicación y Templates Canónicos

*Definición de metadatos de integración, envelopes agnósticos, puertos de mensajería y extracción a `.agent/templates/`.*

- [x] **Value Objects & Event Envelope**
  - Archivo: `src/domain/shared/events/event_envelope.py` (`id`, `event_type`, `payload`, `correlation_id`, `occurred_on`).
  - Template canónico: `.agent/templates/domain/events/event_envelope.tt.py`.
  - Test template: `.agent/templates/domain/events/test_event_envelope.tt.py`.
- [x] **Puertos de Broker y Consumo (Application Ports)**
  - Archivo: `src/application/shared/ports/message_broker_port.py` (`publish(queue/topic, envelope)`).
  - Archivo: `src/application/shared/ports/event_consumer_port.py` (`subscribe(topic, handler)`).
  - Template canónico: `.agent/templates/application/shared/ports/message_broker_port.tt.py`.
  - Test template: `.agent/templates/application/shared/ports/test_message_broker_port.tt.py`.
  - Template canónico: `.agent/templates/application/shared/ports/event_consumer_port.tt.py`.
  - Test template: `.agent/templates/application/shared/ports/test_event_consumer_port.tt.py`.
- [x] **Broker en Memoria para Pruebas (Fake / InMemory Broker)**
  - Archivo: `src/infrastructure/messaging/in_memory/in_memory_message_broker.py` (implementa `MessageBrokerPort` y `EventConsumerPort` usando streams en memoria con `anyio`).
  - Template canónico: `.agent/templates/infrastructure/messaging/in_memory/in_memory_message_broker.tt.py`.
  - Test template: `.agent/templates/infrastructure/messaging/in_memory/test_in_memory_message_broker.tt.py`.
- [x] **Tests Unitarios de Contratos y Envelopes (`anyio`)**
  - Archivo: `tests/unit/domain/test_event_envelope.py`
  - Archivo: `tests/unit/application/test_message_broker_ports.py`
  - Archivo: `tests/unit/infrastructure/messaging/test_in_memory_message_broker.py`

---

### Fase 2: Infraestructura del Broker RabbitMQ (`aio-pika` & `anyio`)

*Implementación concreta de conexión resiliente, topología de colas duraderas, confirmaciones y DLQ.*

- [x] **Dependencias en `pyproject.toml`**
  - Agregar `aio-pika>=9.4,<10.0` para AMQP 0-9-1 asíncrono sobre `anyio`.
- [x] **Gestor de Conexión Resiliente**
  - Archivo: `src/infrastructure/messaging/rabbitmq/rabbitmq_connection_manager.py` (reconexión automática ante caídas del broker).
  - Template canónico: `.agent/templates/infrastructure/messaging/rabbitmq/rabbitmq_connection_manager.tt.py`.
- [x] **Configuración de Topología (Exchanges, Queues & DLQ)**
  - Archivo: `src/infrastructure/messaging/rabbitmq/rabbitmq_topology_config.py`.
  - Exchange: `ai_platform.events` (Tipo: Topic, durable).
  - Queue principal: `conversation.llm_processing.queue` (durable, dead-letter-exchange a DLQ).
  - Dead Letter Queue: `conversation.llm_processing.dlq` (durable).
  - Routing key: `conversation.message.appended`.
  - Template canónico: `.agent/templates/infrastructure/messaging/rabbitmq/rabbitmq_topology_config.tt.py`.
  - Test template: `.agent/templates/infrastructure/messaging/rabbitmq/test_rabbitmq_connection_and_topology.tt.py`.
- [x] **Adaptadores de Publicación y Consumo**
  - Archivo: `src/infrastructure/messaging/rabbitmq/rabbitmq_publisher_adapter.py` (implementa `MessageBrokerPort`).
  - Archivo: `src/infrastructure/messaging/rabbitmq/rabbitmq_consumer_adapter.py` (soporte de `ack`, `nack`, `reject` y prefetch count).
  - Template canónico: `.agent/templates/infrastructure/messaging/rabbitmq/rabbitmq_publisher_adapter.tt.py`.
  - Template canónico: `.agent/templates/infrastructure/messaging/rabbitmq/rabbitmq_consumer_adapter.tt.py`.
  - Test template: `.agent/templates/infrastructure/messaging/rabbitmq/test_rabbitmq_adapters.tt.py`.
- [x] **Tests Unitarios y de Integración de RabbitMQ**
  - [x] Archivo: `tests/unit/infrastructure/messaging/test_rabbitmq_adapters.py` (usando mocks/stubs de canal).
  - [x] Archivo: `tests/integration/infrastructure/messaging/test_rabbitmq_publisher_consumer.py` (contra contenedor real de RabbitMQ).

---

### Fase 3: Outbox Publisher Relay (Garantía At-Least-Once sobre SQL Server)

*Servicio poller concurrente para mover eventos de `outbox_messages` hacia RabbitMQ.*

- [ ] **Extensión de `OutboxStatus`**
  - Actualizar `OutboxStatus` con el estado `PUBLISHED` (`PENDING` $\rightarrow$ `PUBLISHED` $\rightarrow$ `COMPLETED` / `FAILED`).
- [ ] **Servicio Outbox Relay con Concurrencia Estructurada (`anyio`)**
  - Archivo: `src/infrastructure/persistence/outbox/outbox_relay_service.py`.
  - Consulta registros con `select(OutboxMessageModel).with_for_update(skip_locked=True)` (compilada a `WITH (UPDLOCK, READPAST)` en dialecto MSSQL) evitando condiciones de carrera entre múltiples instancias del relay.
  - Publica el `EventEnvelope` hacia RabbitMQ mediante `MessageBrokerPort`.
  - Marca atómicamente el estado a `PUBLISHED` con timestamp de despacho.
  - Bucle de polling resiliente con `anyio.sleep` y cancelación ordenada ante shutdown.
  - Template canónico: `.agent/templates/infrastructure/shared/persistence/outbox/outbox_relay.tt.py`.
  - Test template: `.agent/templates/infrastructure/shared/persistence/outbox/test_outbox_relay.tt.py`.
- [ ] **Tests de Concurrencia de Outbox Relay**
  - Archivo: `tests/unit/infrastructure/persistence/test_outbox_relay_service.py`.
  - Archivo: `tests/integration/infrastructure/persistence/test_outbox_relay_concurrency.py` (múltiples pollers concurrentes contra SQL Server 2022).

---

### Fase 4: Proceso Worker Autónomo (`src/worker.py`)

*Entrypoint y contenedor desacoplado para inferencia LLM en segundo plano.*

- [ ] **Ensamblador de Dependencias del Worker (Composition Root)**
  - Archivo: `src/worker_container.py` (ensambla conexión a SQL Server, `MssqlUnitOfWork`, `LlmClientPort` y `RabbitMQConsumerAdapter` sin dependencias de FastAPI).
- [ ] **Handler Consumidor de Inferencia LLM**
  - Archivo: `src/application/conversations/workers/llm_message_processing_worker.py`.
  - Deserializa `EventEnvelope`, procesa la inferencia del modelo LLM mediante `LlmClientPort`.
  - Persiste la respuesta del asistente mediante `AppendAssistantMessageHandler` dentro de una transacción `UnitOfWork`.
  - Emite `ack()` si el procesamiento es exitoso o `reject(requeue=False)` hacia DLQ ante error irrecuperable.
- [ ] **Script Entrypoint del Proceso Worker**
  - Archivo: `src/worker.py` (manejo de señales POSIX `SIGINT`/`SIGTERM` con `anyio` para graceful shutdown).
  - Templates canónicos: `.agent/templates/interfaces/worker/worker_entrypoint.tt.py` y `test_worker_entrypoint.tt.py`.
- [ ] **Tests de Ciclo Completo del Worker**
  - Archivo: `tests/unit/application/test_llm_message_processing_worker.py`.
  - Archivo: `tests/integration/workers/test_llm_message_processing_worker.py`.

---

### Fase 5: Docker Compose, ADR y Sincronización del Diagrama Vivo

*Orquestación multi-contenedor y formalización arquitectónica.*

- [ ] **Actualización de `docker-compose.yml`**
  - Servicio `api`: Proceso FastAPI web (puerto 8000).
  - Servicio `worker`: Proceso autónomo `python -m src.worker`.
  - Servicio `broker`: RabbitMQ (imagen `rabbitmq:3-management-alpine` con puertos 5672 y 15672).
  - Servicio `db`: Microsoft SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`, puerto 1433).
- [ ] **Documento de Decisión Arquitectónica (ADR)**
  - Archivo: `.agent/architecture/decisions/0003-decoupled-worker-and-rabbitmq.md`.
- [ ] **Actualización del Diagrama Vivo**
  - Archivo: `.agent/architecture/system-map.mermaid.md` (separación explícita de nodos y pods entre API y Worker).

---

## 🔍 Criterios de Aceptación del Slice 4

1. **Aislamiento Total de Procesos:** Si el servicio `api` se detiene o reinicia, el proceso `worker` continúa consumiendo la cola sin interrupción. Si el `worker` se reinicia, los mensajes permanecen seguros y encolados en RabbitMQ sin pérdida de datos.
2. **Resiliencia ante Fallos del LLM:** Si la API del LLM retorna error o timeout, el mensaje se reintenta según política de backoff o se mueve a la `Dead Letter Queue` (`conversation.llm_processing.dlq`) con trazabilidad completa.
3. **Escalabilidad Horizontal y Concurrencia:** Múltiples instancias del `worker` y del `OutboxRelay` pueden operar en paralelo compitiendo por eventos sin duplicar publicaciones ni procesamientos (`UPDLOCK, READPAST` en SQL Server y prefetch en RabbitMQ).
4. **Concurrencia Estructurada con `anyio`:** Todas las operaciones asíncronas de fondo, reconexiones, bucles de sondeo y pruebas utilizan `@pytest.mark.anyio` y `anyio.create_task_group()`.
5. **Verificación Automatizada Completa:** `make check-all` y `make coverage` pasan al 100% cumpliendo los estándares de Ruff, Pyright (0 errores), Bandit SAST y cobertura $\ge 90\%$.
