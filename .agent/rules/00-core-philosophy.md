---
trigger: model_decision
description: Rules for Clean Architecture, DDD, CQRS, and Ports & Adapters. Activate when designing, creating, refactoring, or reviewing code, classes, or layer dependencies across domain, application, infrastructure, or interfaces.
---

# 00 — Core Architecture & Engineering Philosophy

Este documento establece los invariantes arquitectónicos del proyecto `ai-conversation-platform`. Cualquier propuesta de código o refactorización que viole estas reglas será rechazada automáticamente.

---

## 1. Principios Fundamentales

1. **Clean / Hexagonal Architecture (Ports & Adapters):**
   - El núcleo del negocio es 100% agnóstico a frameworks, bases de datos, buses de mensajes o protocolos de transporte.
   - Las dependencias apuntan **estrictamente hacia adentro**. La capa externa conoce a la interna; la interna NUNCA conoce a la externa.

2. **Domain-Driven Design (DDD) Táctico:**
   - La lógica de negocio reside exclusivamente en **Entidades**, **Value Objects** y **Servicios de Dominio**.
   - Los cambios de estado dentro del dominio emiten **Domain Events** inmutables.
   - Toda interacción con persistencia se realiza a través de contratos abstractos (**Ports**).

3. **CQRS (Command Query Responsibility Segregation):**
   - Las operaciones de escritura (**Commands**) mutan el estado y disparan eventos de dominio. No devuelven entidades completas; devuelven identificadores o confirmación de ejecución.
   - Las operaciones de lectura (**Queries**) obtienen DTOs de lectura directos optimizados para el consumidor, sin alterar el estado.

4. **Vertical Slice Architecture:**
   - Cada entrega de funcionalidad es un corte vertical navegable desde la interfaz HTTP hasta la persistencia y eventos (Slice 1 = Create Conversation, Slice 2 = Send Message & Streaming).

---

## 2. Matriz de Dependencias entre Capas

```txt
[ Interfaces (HTTP / CLI) ]  -->  [ Application (Commands / Queries) ]  -->  [ Domain (Core) ]
           │                                     │                              ▲
           │                                     │                              │
           └──> [ Infrastructure (Adapters) ] ───┴──────────────────────────────┘
```

| Capa                 | Responsabilidad                                                                                                             | Dependencias Permitidas                                                  | PROHIBICIONES ESTRICTAS                                                                               |
| :------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| **`domain`**         | Entidades, invariantes, eventos puros, puertos abstractos.                                                                  | Solo Python Standard Library (`dataclasses`, `uuid`, `datetime`, `abc`). | **PROHIBIDO** importar FastAPI, Pydantic, SQLAlchemy, HTTPX o cualquier SDK externo.                  |
| **`application`**    | Orquestación de casos de uso (Handlers), DTOs de comandos/queries, puertos de I/O (`UnitOfWorkPort`, `EventPublisherPort`). | `domain` y Python Standard Library.                                      | **PROHIBIDO** invocar directamente drivers de red, bases de datos o frameworks web.                   |
| **`infrastructure`** | Implementación física de puertos (Driven Adapters): Repositorios en memoria/Postgres, HTTPX, Outbox dispatcher.             | `domain`, `application`, librerías externas (SQLAlchemy, httpx, etc.).   | **PROHIBIDO** contener reglas de negocio o alterar entidades saltándose sus métodos.                  |
| **`interfaces`**     | Puntos de entrada (Driver Adapters): Routers FastAPI, esquemas Pydantic de entrada/salida.                                  | `application`, `domain`, FastAPI, Pydantic.                              | **PROHIBIDO** escribir lógica de negocio o queries directas a la base de datos dentro de los routers. |

---

## 3. Invariantes de Diseño de Código

### A. Dominio y Agregados

- Las entidades extienden de `AggregateRoot` y controlan sus colecciones internamente.
- Las mutaciones de estado se realizan mediante métodos explícitos con nombres de negocio (ej. `conversation.append_message(...)`), nunca mutando propiedades directamente desde afuera.
- Toda regla de validación de negocio lanza excepciones específicas derivadas de `DomainError` o `ValueError`.

### B. Capa de Aplicación

- Cada comando tiene un archivo de DTO (`*_command.py`) y un archivo de ejecución (`*_command_handler.py`).
- Los handlers reciben únicamente sus dependencias inyectadas por constructor como abstracciones (puertos / `ABC`).
- El ciclo transaccional se gestiona mediante el puerto `UnitOfWorkPort`.

### C. Persistencia y Outbox Pattern

- Ningún evento de integración se envía a un broker externo antes de garantizar la persistencia del estado en la misma transacción lógica.
- La infraestructura almacena eventos en la tabla/colección `outbox` como parte de la unidad de trabajo antes de su publicación asíncrona.

---

## 4. Regla de Oro para el Agente Autónomo

Si para resolver un problema necesitas importar una librería externa dentro de `src/domain/` o `src/application/`, **tu diseño es erróneo**. Reubica la dependencia detrás de un puerto abstracto (`ABC`) e impleméntala en `src/infrastructure/`.