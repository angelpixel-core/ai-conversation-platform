# Roadmap de Implementación — Slice 3: Persistent Storage with Microsoft SQL Server & SQLModel (Transactional Outbox DB)

Este documento detalla la ruta de desarrollo, migración a persistencia relacional industrial con **Microsoft SQL Server (MSSQL)**, soporte atómico para el patrón **Transactional Outbox** y verificación para el tercer slice vertical de **ai-conversation-platform**.

---

## 🎯 Objetivo del Slice 3

Reemplazar los adaptadores temporales en memoria por adaptadores de producción respaldados por **Microsoft SQL Server**:

1. **Persistencia Relacional con SQLModel (SQLAlchemy 2.0):** Modelar las tablas físicas `conversations`, `messages` y `outbox_messages` garantizando aislamiento total del Dominio mediante el patrón *Data Mapper*.
2. **Transactional Outbox Físico en MSSQL:** Garantizar atomicidad estricta (`ACID`): cuando se crea una conversación o se añade un mensaje, la entidad y el evento del outbox se insertan bajo la misma transacción de SQL Server (`BEGIN TRANSACTION ... COMMIT`). Si algo falla, se ejecuta `ROLLBACK` sin dejar datos huérfanos.
3. **Gestión de Esquemas con Alembic:** Versionado y aplicación de migraciones de base de datos para el dialecto de Microsoft SQL Server.
4. **Desacoplamiento e Inversión de Control (Ports & Adapters):** El Dominio y los Casos de Uso (`Application`) no cambian una sola línea de código; el sistema permite alternar entre `PERSISTENCE_DRIVER=in_memory` y `PERSISTENCE_DRIVER=mssql` mediante configuración.

---

## 🏗️ Desglose Arquitectónico del Flujo

1. **Data Mapper e Invariantes de Dominio:**
   - La entidad `Conversation` (Aggregate Root) y sus Value Objects (`Message`) continúan viviendo exclusivamente en la capa de Dominio, sin heredar de `SQLModel` ni importar librerías de base de datos.
   - En la capa de Infraestructura, `ConversationDataMapper` se encarga de convertir de `Conversation` a `ConversationModel` / `MessageModel` y reconstruir el agregado al recuperarlo con `Conversation.reconstitute(...)`.

2. **Unit of Work y Transacciones en MSSQL:**
   - `MssqlUnitOfWork` implementa el puerto `UnitOfWork`.
   - Abre una sesión de SQLModel ligada a una transacción de SQL Server.
   - Provee los repositorios `conversations` y `outbox`.
   - Si el caso de uso finaliza exitosamente, ejecuta `session.commit()`. Ante cualquier excepción no capturada, ejecuta `session.rollback()` y cierra la sesión en el `__exit__`.

3. **Outbox Dispatcher sobre Tabla Física:**
   - El `OutboxDispatcher` implementado en el Slice 2 interactúa de forma transparente con `MssqlOutboxRepository`, consultando mensajes con estado `pending`, entregándolos al bus de eventos y marcándolos como `dispatched` o `failed`.

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Infraestructura — Modelos Físicos & Data Mappers (SQLModel & MSSQL)

*Modelos de tablas relacionales y traducción desacoplada con el Dominio.*

- [x] **Dependencias de Base de Datos en `pyproject.toml`**
  - Instalar `sqlmodel`, `pymssql` (o `aioodbc`) y `alembic`.
- [x] **Modelos Físicos Relacionales**
  - Archivo: `src/infrastructure/persistence/mssql/models.py`
  - Modelos: `ConversationModel`, `MessageModel`, `OutboxMessageModel` (claves primarias UUID, foreign keys en cascada, índices y timestamps UTC).
- [x] **Mapeador Bidireccional (Data Mapper)**
  - Archivo: `src/infrastructure/persistence/mssql/mapper.py`
  - Clase: `ConversationDataMapper` (`to_domain`, `to_model`, `message_to_model`).
- [x] **Tests Unitarios de Mapeo**
  - Archivo: `tests/unit/infrastructure/mssql/test_conversation_mapper.py`

---

### Fase 2: Infraestructura — Conexión, Repositorios & Unit of Work

*Implementación de los Driven Adapters de persistencia sobre SQL Server.*

- [x] **Fábrica de Conexión y Sesiones MSSQL**
  - Archivo: `src/infrastructure/persistence/mssql/connection.py`
  - Funciones para inicializar el `Engine` y `session_factory` con pooling de conexiones y timeouts configurables.
- [x] **Adaptador de Repositorio de Conversaciones**
  - Archivo: `src/infrastructure/persistence/mssql/repository.py` (`MssqlConversationRepository`)
  - Implementa `ConversationRepository` (`add`, `get`, `list`).
- [x] **Adaptador de Repositorio de Outbox Físico**
  - Archivo: `src/infrastructure/persistence/mssql/outbox_repository.py` (`MssqlOutboxRepository`)
  - Métodos: `save`, `add`, `get_by_id`, `get_pending`, `mark_as_dispatched`, `mark_as_completed`, `mark_as_failed`.
- [x] **Adaptador Unit of Work Transaccional**
  - Archivo: `src/infrastructure/persistence/mssql/unit_of_work.py` (`MssqlUnitOfWork`)
  - Implementa `UnitOfWork` gestionando transacciones ACID atómicas.

---

### Fase 3: Migraciones y Esquema de Base de Datos (Alembic & Docker)

*Versionado de esquema relacional y orquestación local.*

- [ ] **Inicialización de Alembic**
  - Archivos: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`.
  - Configurar `target_metadata = SQLModel.metadata`.
- [ ] **Generación de la Migración Inicial**
  - Archivo: `migrations/versions/0001_initial_mssql_schema.py`
  - Creación de tablas `conversations`, `messages` y `outbox_messages` con índices foráneos.
- [ ] **Verificación del Contenedor Docker**
  - Archivo: `docker-compose.yml` (validar servicio `mssql_db` con SQL Server 2022 y base de datos `ChatbotDB`).

---

### Fase 4: Tests de Integración de Persistencia Real (TDD)

*Pruebas automáticas contra base de datos relacional.*

- [ ] **Fixtures de Base de Datos de Pruebas**
  - Archivo: `tests/integration/infrastructure/mssql/conftest.py` (creación limpia de esquema y sesión de test).
- [ ] **Tests de Integración de Repositorio**
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_conversation_repository.py`
  - Verificar guardado de conversación, agregado de mensajes y recuperación completa.
- [ ] **Tests de Integración de Unit of Work y Rollback Atómico**
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_unit_of_work.py`
  - Verificar que ante un error en la transacción, el mensaje y el outbox hacen rollback simultáneo.
- [ ] **Tests de Integración de Outbox Físico**
  - Archivo: `tests/integration/infrastructure/mssql/test_mssql_outbox_repository.py`
  - Verificar flujo completo: inserción -> lectura de pendientes -> actualización de estado a `dispatched`/`failed`.

---

### Fase 5: Configuración (Settings), Ensamble & Documentación

- [ ] **Configuración Tipada con Pydantic Settings**
  - Archivo: `src/infrastructure/shared/config/settings.py` (`DatabaseSettings`, variable `PERSISTENCE_DRIVER`).
- [ ] **Inyección Dinámica de Persistencia en `src/main.py`**
  - Soporte transparente para elegir entre `MssqlUnitOfWork` e `InMemoryUnitOfWork` sin alterar contratos.
- [ ] **Actualización del Diagrama Vivo del Sistema**
  - Archivo: `.agent/architecture/system-map.mermaid.md` (incorporar nodos de MSSQL Models, Mappers, Repositorios y UoW).
- [ ] **Verificación de Calidad Completa**
  - Ejecutar `make check-all` (Ruff format, lint, Pyright, Bandit y Pytest).

---

## 🔍 Criterios de Aceptación del Slice 3

1. **Persistencia Atómica en SQL Server:** Al ejecutar `POST /conversations` o `POST /conversations/{id}/messages`, la información del agregador y el registro del outbox se guardan en la misma transacción física de Microsoft SQL Server.
2. **Rollback Verificado ante Fallas:** Si la inserción del mensaje o del outbox falla, la base de datos no retiene datos parciales.
3. **Cero Violaciones de Capas:** Ni `domain` ni `application` importan SQLModel, SQLAlchemy, pymssql ni ningún componente de base de datos.
4. **Migraciones Reproducibles:** El comando de Alembic aplica el esquema completo en una instancia limpia de SQL Server sin errores de sintaxis T-SQL.
5. **Suite de Pruebas en Verde:** Todos los tests unitarios e integrados pasan exitosamente reportando cobertura superior al 90%.
