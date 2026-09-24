---
id: STRUCTURE
aliases: []
tags: []
---

```txt
├── Dockerfile
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture.md
│   └── roadmap.md
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   │   └── test_conversation_entity.py
│   │   └── application/
│   │       └── test_create_conversation_command_handler.py
│   ├── integration/
│   │   ├── infrastructure/
│   │   │   └── test_conversation_repository.py
│   │   └── api/
│   │       └── test_conversations_router.py
│   └── conftest.py
└── src/
    ├── __init__.py
    ├── container.py                          <-- Assembly Root / Contenedor de Inyección
    ├── main.py                               <-- Entrypoint / Inicialización FastAPI
    │
    ├── domain/                               <-- CAPA DE DOMINIO (Reglas Puras)
    │   ├── __init__.py
    │   ├── shared/
    │   │   ├── __init__.py
    │   │   ├── domain_error.py
    │   │   └── aggregate_root.py
    │   └── conversations/
    │       ├── __init__.py
    │       ├── conversation_entity.py        <-- Entidad Agregada
    │       ├── conversation_events.py        <-- Eventos de Dominio (ConversationCreated)
    │       ├── conversation_exceptions.py    <-- Excepciones de Negocio
    │       └── conversation_repository_port.py <-- Puerto del Repositorio (ABC)
    │
    ├── application/                          <-- CAPA DE APLICACIÓN (Casos de Uso)
    │   ├── __init__.py
    │   ├── shared/
    │   │   ├── __init__.py
    │   │   └── ports/
    │   │       ├── __init__.py
    │   │       ├── event_publisher_port.py   <-- Puerto del Publicador de Eventos
    │   │       ├── http_client_port.py       <-- Puerto para el cliente LLM futuro
    │   │       └── unit_of_work_port.py      <-- Puerto de la Unidad de Trabajo
    │   └── conversations/
    │       ├── __init__.py
    │       ├── commands/
    │       │   ├── __init__.py
    │       │   ├── create_conversation_command.py          <-- DTO del Comando
    │       │   └── create_conversation_command_handler.py  <-- Ejecutor del Comando
    │       ├── queries/
    │       │   ├── __init__.py
    │       │   ├── get_conversation_by_id_query.py         <-- DTO de la Consulta
    │       │   ├── get_conversation_by_id_query_handler.py <-- Ejecutor de Consulta
    │       │   ├── list_conversations_query.py             <-- DTO Listar
    │       │   └── list_conversations_query_handler.py     <-- Ejecutor Listar
    │       └── events/
    │           ├── __init__.py
    │           ├── conversation_created_event.py           <-- DTO Evento Aplicación
    │           └── conversation_created_event_handler.py   <-- Manejador de Eventos
    │
    ├── infrastructure/                       <-- CAPA DE INFRAESTRUCTURA (Adapta I/O)
    │   ├── __init__.py
    │   ├── logging/
    │   │   ├── __init__.py
    │   │   └── logging_config.py
    │   ├── telemetry/
    │   │   ├── __init__.py
    │   │   └── telemetry_service.py
    │   ├── http_client/
    │   │   ├── __init__.py
    │   │   └── httpx_client_adapter.py       <-- Adaptador del cliente HTTP
    │   ├── persistence/
    │   │   ├── __init__.py
    │   │   ├── in_memory/
    │   │   │   ├── __init__.py
    │   │   │   ├── in_memory_conversation_repository_adapter.py
    │   │   │   └── in_memory_unit_of_work_adapter.py
    │   │   └── outbox/                       <-- Implementación Patrón Outbox
    │   │       ├── __init__.py
    │   │       ├── outbox_message_model.py   <-- Modelo de mensaje retenido
    │   │       ├── outbox_repository_adapter.py
    │   │       └── outbox_dispatcher_service.py <-- Worker/Dispatcher de Eventos
    │   └── messaging/
    │       ├── __init__.py
    │       └── in_memory_event_publisher_adapter.py
    │
    └── interfaces/                           <-- CAPA DE INTERFACES (Driver Adapters)
        ├── __init__.py
        └── http/
            ├── __init__.py
            ├── conversations_router.py       <-- Adaptador HTTP (FastAPI APIRouter)
            ├── conversations_schemas.py      <-- Pydantic DTOs (Request / Response)
            └── health_router.py              <-- Endpoint /health
```
