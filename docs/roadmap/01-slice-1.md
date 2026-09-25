---
id: ROADMAP
aliases: []
tags: []
---

# Roadmap de Implementación — Slice 1: Create Conversation

Este documento detalla la ruta de desarrollo, lectura y verificación para el primer slice vertical de **ai-conversation-platform**.

---

## 🎯 Objetivo del Slice 1

Establecer el núcleo arquitectónico basado en Clean Architecture / DDD, CQRS e Inyección de Dependencias sin dependencias externas pesadas, permitiendo inicializar sesiones de conversación de forma transaccional mediante persistencia en memoria y una API HTTP.

---

## 🏗️ Estrategia de Testing (Estándar Python / Pytest)

Se adopta el patrón de suite externa en `tests/` reflejando la estructura de `src/`:

- **Unit Tests (`tests/unit/`)**: Prueban la lógica de negocio pura de entidades y command handlers sin I/O, sin base de datos y sin servidor HTTP.
- **Integration Tests (`tests/integration/`)**: Verifican contratos de repositorios y adaptadores de infraestructura.
- **E2E / API Tests (`tests/integration/api/` o `tests/integration/test_http.py`)**: Prueban el ciclo HTTP completo usando `httpx` / `TestClient` contra la aplicación FastAPI.

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Configuración del Entorno, CI/CD y Base del Proyecto

- [x] **Configuración del proyecto y dependencias**
  - Archivo: `pyproject.toml`
  - Dependencias core: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`
  - Dependencias dev/test/QA: `pytest`, `pytest-cov`, `httpx`, `ruff`, `pyright`, `bandit`, `pip-audit`
- [x] **Dockerización base y Orquestación**
  - Archivos: `Dockerfile`, `docker-compose.yml` (API + Microsoft SQL Server)
- [x] **Automatización con Makefile**
  - Archivo: `Makefile` (`make test`, `make coverage`, `make check-all`, `make docker-up`)
- [x] **Pipeline de CI/CD (GitHub Actions)**
  - Archivo: `.github/workflows/ci.yml` (Lint, Typecheck, Security SAST, Tests & Coverage)
- [x] **Documentación arquitectónica inicial**
  - Archivos: `README.md`, `STRUCTURE.md`, `ROADMAP.md`, `docs/architecture.md`, `docs/roadmap.md`

---

### Fase 2: Capa de Dominio (Domain Layer)

_Núcleo agnóstico sin dependencias a frameworks._

- [x] **Base para Agregados y Eventos**
  - [x] Archivo: `src/domain/shared/aggregate_root.py`
  - [x] Archivo: `src/domain/shared/domain_event.py`
  - [x] Archivo: `src/domain/shared/domain_error.py`
- [x] **Entidad de Dominio**
  - [x] Archivo: `src/domain/conversations/entities/conversation.py`
- [x] **Eventos de Dominio**
  - [x] Archivo: `src/domain/conversations/events/conversation_created.py` (`ConversationCreatedDomainEvent`)
- [x] **Puerto de Persistencia (Driven Port)**
  - [x] Archivo: `src/domain/conversations/ports/conversation_repository.py`
- [x] **Tests Unitarios del Dominio**
  - [x] Archivo: `tests/unit/domain/test_conversation.py`
  - [x] Archivo: `tests/unit/domain/shared/test_aggregate_root.py`

---

### Fase 3: Capa de Aplicación (Application Layer - CQRS)

_Orquestación de casos de uso y definición de puertos compartidos._

- [x] **Puertos de Aplicación (Abstracciones de I/O)**
  - [x] Archivo: `src/application/shared/ports/unit_of_work.py`
  - [x] Archivo: `src/application/shared/ports/event_publisher.py`
  - [x] Archivo: `src/application/shared/ports/http_client.py`
- [x] **Comando: Create Conversation**
  - [x] Comando y Handler: `src/application/conversations/commands/create_conversation.py`
- [ ] **Query: Get Conversation & List (Lecturas básicas)**
  - [ ] Query DTO & Handler: `src/application/conversations/queries/get_conversation.py`
  - [ ] Query List DTO & Handler: `src/application/conversations/queries/list_conversations.py`
- [x] **Tests Unitarios de Aplicación**
  - [x] Archivo: `tests/unit/application/test_create_conversation.py`

---

### Fase 4: Capa de Infraestructura (Infrastructure Layer)

_Implementación física de los puertos definidos en dominio y aplicación._

- [x] **Adaptador de Persistencia en Memoria**
  - [x] Repositorio: `src/infrastructure/persistence/in_memory/repository.py`
  - [x] Unit of Work: `src/infrastructure/persistence/in_memory/unit_of_work.py`
- [x] **Adaptadores de Servicios Compartidos**
  - [x] HTTP Client Adapter: `src/infrastructure/shared/http_client/httpx_client.py`
  - [x] Telemetry Adapter: `src/infrastructure/shared/telemetry/telemetry.py`
  - [x] Logging Config: `src/infrastructure/shared/logging/config.py`
- [x] **Estructura Base para Outbox Pattern (Preparación Slice 2)**
  - [x] Modelo / Dispatcher Outbox en memoria: `src/infrastructure/shared/persistence/outbox/in_memory.py`

---

### Fase 5: Capa de Interfaces (Driver Adapters - HTTP FastAPI)

_Punto de entrada para el usuario y traducción de peticiones._

- [x] **Esquemas DTO HTTP (Pydantic v2)**
  - [x] Archivo: `src/interfaces/http/schemas.py`
- [x] **Controladores / Routers HTTP**
  - [x] API Router de Conversaciones y Salud: `src/interfaces/http/api.py`
- [x] **Tests de Endpoints / Integración HTTP**
  - [x] Archivo: `tests/integration/test_http.py`

---

### Fase 6: Ensamble, Inyección de Dependencias y Entrypoint

_Conexión de todas las capas sin acoplamiento._

- [x] **Entrypoint de la Aplicación e Inicialización FastAPI**
  - [x] Archivo: `src/main.py`

---

## 🔍 Criterios de Aceptación del Slice 1

1. [x] `make check-all` ejecuta todas las pruebas unitarias, de integración, linter (`ruff`), chequeo de tipos (`pyright`), seguridad (`bandit`), auditoría de dependencias (`pip-audit`) y cobertura pasando al 100%.
2. [x] `curl -X POST http://localhost:8000/conversations -H "Content-Type: application/json" -d '{"title": "Test Chat"}'` retorna código HTTP `201 Created` con el ID y fecha generados.
3. [ ] `curl http://localhost:8000/conversations/{id}` retorna el detalle de la conversación creada (Pendiente Query Handler).
4. [x] Las capas `domain` y `application` no contienen ningún `import fastapi`, `import httpx` ni dependencias a librerías externas de I/O.
