---
id: docs-roadmap-slice-02
aliases: []
tags: []
---

# Roadmap de Implementación — Slice 2: Send Message & Streaming Response

Este documento detalla la ruta de desarrollo, orquestación asíncrona y verificación para el segundo slice vertical de **ai-conversation-platform**.

---

## 🎯 Objetivo del Slice 2
Permitir que un cliente envíe un mensaje a una conversación existente, reciba confirmación inmediata (`202 Accepted` / `200 OK`), persista el mensaje de usuario transaccionalmente en la base de datos junto a un evento de Outbox, y habilite el streaming reactivo token a token (vía Server-Sent Events / SSE o WebSockets) mientras el LLM genera la respuesta.

---

## 🏗️ Desglose Arquitectónico del Flujo

1. **Recepción del Mensaje (Command HTTP):**
   - El cliente envía `POST /conversations/{id}/messages` con `{"content": "..."}`.
   - El router traduce a `SendMessageCommand`.
   - `SendMessageCommandHandler` recupera el agregado `Conversation`, invoca `conversation.append_message(role="user", content=...)`.
   - La entidad valida invariantes y emite `MessageAppendedDomainEvent`.
   - Se persiste atómicamente a través de `UnitOfWork` (guardando la conversación y registrando el evento en `Outbox`).
   - El endpoint responde de inmediato (`202 Accepted` o `200 OK`).

2. **Despacho Asíncrono & Outbox Dispatcher:**
   - `OutboxDispatcherService` detecta el evento pendiente en segundo plano (`asyncio.create_task` o worker).
   - Marca el evento como en proceso y lo envía a través de `EventPublisherPort`.

3. **Orquestación con el LLM & Streaming (Driver / Driven Ports):**
   - El consumidor del evento o el servicio de streaming invoca `LlmClientPort` (adaptador `HttpxLlmClientAdapter` o SDK oficial).
   - El LLM devuelve un generador asíncrono (`AsyncIterator[str]`).
   - El endpoint `GET /conversations/{id}/messages/stream` (o conexión SSE abierta) transmite los deltas/tokens al cliente en tiempo real.
   - Al finalizar el stream, se añade el mensaje completo del `assistant` a la conversación y se confirma la persistencia final.

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio (Domain Layer)
*Extensión del agregado para soportar roles, tokens y validaciones.*

- [x] **Value Object de Mensaje**
  - Archivo: `src/domain/conversations/value_objects/message.py`
  - Encapsula `role` (`user`, `assistant`, `system`), `content`, `created_at`.
- [ ] **Extensión de la Entidad de Dominio**
  - Archivo: `src/domain/conversations/entities/conversation.py`
  - Validaciones de longitud de mensaje, contenido no vacío y alternancia de turnos.
- [ ] **Nuevos Eventos de Dominio**
  - Archivo: `src/domain/conversations/events/message_appended.py` (`MessageAppendedDomainEvent`)
  - Archivo: `src/domain/conversations/events/assistant_response_completed.py` (`AssistantResponseCompletedDomainEvent`)
- [ ] **Puerto para Cliente LLM (Driven Port)**
  - Archivo: `src/application/shared/ports/llm_client.py`
  - Contrato abstracto: `LlmClientPort` con método `stream_chat(messages, ...)` retornando `AsyncIterator[str]`.
- [ ] **Tests Unitarios de Dominio**
  - Archivo: `tests/unit/domain/test_conversation_messaging.py`

---

### Fase 2: Aplicación (Application Layer - CQRS & Handlers)
*Comandos de mensajería y orquestación del streaming.*

- [ ] **Comando: Send Message (Ingesta de usuario)**
  - Archivo: `src/application/conversations/commands/send_message.py` (`SendMessageCommand`, `SendMessageHandler`)
- [ ] **Comando: Append Assistant Message (Cierre de stream)**
  - Archivo: `src/application/conversations/commands/append_assistant_message.py` (`AppendAssistantMessageCommand`, `AppendAssistantMessageHandler`)
- [ ] **Query: Stream Conversation Response (Lectura reactiva)**
  - Archivo: `src/application/conversations/queries/stream_conversation.py` (`StreamConversationQuery`, `StreamConversationQueryHandler`)
- [ ] **Tests Unitarios de Aplicación**
  - Archivo: `tests/unit/application/test_send_message_command.py`
  - Archivo: `tests/unit/application/test_stream_conversation_query.py`

---

### Fase 3: Infraestructura (Infrastructure Layer)
*Outbox pattern y conexión con el proveedor de IA.*

- [ ] **Implementación del Patrón Outbox**
  - Modelo & Repositorio: `src/infrastructure/shared/persistence/outbox/in_memory.py`
  - Dispatcher Worker: `src/infrastructure/shared/persistence/outbox/dispatcher.py`
- [ ] **Adaptador de LLM (Streaming Client)**
  - Adaptador Fake para pruebas: `src/infrastructure/llm/fake_llm_client.py` (`FakeLlmClientAdapter`)
  - Adaptador HTTP/API real: `src/infrastructure/llm/httpx_llm_client.py` (`HttpxLlmClientAdapter`)
- [ ] **Tests de Integración de Infraestructura**
  - Archivo: `tests/integration/infrastructure/test_outbox_dispatcher.py`
  - Archivo: `tests/integration/infrastructure/test_llm_client_adapter.py`

---

### Fase 4: Interfaces (HTTP & SSE / Streaming)
*Endpoints de ingesta y canal de salida en tiempo real.*

- [ ] **Esquemas DTO HTTP (Pydantic v2)**
  - Archivo: `src/interfaces/http/schemas.py` (adicionar `SendMessageRequest`, `MessageResponse`)
- [ ] **Router de Mensajería y Streaming (FastAPI)**
  - Archivo: `src/interfaces/http/api.py` (o `messages_router.py`)
  - Endpoint `POST /conversations/{id}/messages` (`202 Accepted` / `200 OK`)
  - Endpoint `GET /conversations/{id}/stream` (FastAPI `StreamingResponse` con `text/event-stream`)
- [ ] **Tests de Integración de API / Streaming**
  - Archivo: `tests/integration/test_http.py`

---

### Fase 5: Ensamble, Container y Actualización Documental
- [ ] **Inyección de Dependencias**
  - Archivo: `src/main.py` (registrar `LlmClientPort`, `OutboxDispatcher` y nuevos handlers)
- [ ] **Actualización del Diagrama Vivo**
  - Archivo: `.agent/architecture/system-map.mermaid.md`
- [ ] **Verificación de Suite Completa**
  - Ejecución de `pytest` (cobertura total de Slice 1 y Slice 2)

---

## 🔍 Criterios de Aceptación del Slice 2
1. `POST /conversations/{id}/messages` responde `202 Accepted` o `200 OK` en menos de 50ms sin esperar la respuesta del LLM.
2. `GET /conversations/{id}/stream` abre un canal SSE y transmite tokens de forma progresiva.
3. Si el streaming se corta a la mitad por desconexión de red, la integridad de la base de datos se mantiene coherente.
4. El LLM puede ser sustituido por `FakeLlmClientAdapter` durante las suites de test sin requerir claves de API reales ni conexión a internet.