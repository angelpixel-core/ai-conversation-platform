# ARTICLE-[ID]: [Título Técnico del Caso de Uso / Vertical Slice]

> Plantilla agnóstica de lenguaje. Para este proyecto (Python / FastAPI / pytest) usar [`ARTICLE_TEMPLATE.python.md`](ARTICLE_TEMPLATE.python.md).

* **Artículo ID:** ARTICLE-[ID]
* **User Story:** [US-XX: Título de la Historia]
* **Bounded Context:** [e.g. identity]
* **Tipo de Slice:** [Command (Escritura) | Query (Lectura)]
* **Rama de Trabajo:** `feat/[US-XX-slug]`
* **Squash Commit en main:** `pendiente`
* **Fecha:** YYYY-MM-DD
* **Autor / Tech Lead:** [Nombre]

---

## 1. Resumen Ejecutivo y Problema de Negocio

[Descripción concisa del problema de negocio resuelto para los tenants y usuarios. Explicar qué capacidad se incorpora al sistema y cómo impacta en la experiencia o seguridad de la plataforma.]

---

## 2. Diseño Arquitectónico del Vertical Slice

Desglose de la porción vertical implementada conforme a los principios de **Arquitectura Hexagonal + DDD** y [`.agent/rules/00-core-philosophy.md`](../rules/00-core-philosophy.md):

```mermaid
flowchart LR
    A["Driver Adapter\n(HTTP / CLI / MCP / Worker)"] --> B["Application\n(Command/Query Handler)"]
    B --> C["Domain\n(Aggregate / Value Objects)"]
    B --> D["Secondary Port\n(Repository/Cache Port)"]
    D --> E["Driven Adapter\n(Database / Cache / Broker)"]
```

### Componentes Clave del Slice

* **Punto de Entrada (Driver Adapter):** `[ruta del driver adapter]`
* **Mensaje de Aplicación:** `[ruta del command/query]`
* **Orquestador:** `[ruta del handler]`
* **Entidades e Invariantes:** `[ruta del aggregate]`
* **Puertos Secundarios (SPI):** `[ruta de los puertos]`
* **Adaptadores de Infraestructura:** `[ruta de los adaptadores]`

---

## 3. Decisiones de Dominio Táctico y Aislamiento Multitenant

### 3.1. Invariantes y Value Objects

[Explicar cómo se modelaron los conceptos clave como Value Objects inmutables, qué reglas de validación encapsulan y por qué evitan el uso de tipos primitivos (Primitive Obsession).]

### 3.2. Aislamiento por Tenant

[Detallar cómo se garantizó la segregación de datos del tenant en esta funcionalidad específica (validación de tokens, inyección de contexto, filtros obligatorios en repositorios y particionamiento de claves de caché).]

---

## 4. Evidencia de Pruebas (Pirámide Completa)

El desarrollo se condujo bajo **Double-Loop TDD**. A continuación se documenta la evidencia de ejecución en las distintas capas:

### 4.1. Pruebas Unitarias (Domain & Application)

* **Archivos:** `[ruta de tests unitarios]`
* **Comando:** `[comando de tests unitarios]`
* **Resultado:** [Salida real del comando]

### 4.2. Pruebas de Integración (Adapters & Interfaces)

* **Archivos:** `[ruta de tests de integración]`
* **Comando:** `[comando de tests de integración]`
* **Resultado:** [Salida real del comando]

### 4.3. Pruebas de Aceptación BDD (Outer Loop Gherkin)

* **Archivo Feature:** `[ruta del .feature]`
* **Escenario en Verde:**

```gherkin
Scenario: [Nombre del escenario principal validado]
  Given ...
  When ...
  Then ...
```

### 4.4. Pruebas End-to-End (omitir si el slice no tiene UI)

* **Archivo:** `[ruta del test E2E]`
* **Resultado:** [Validación del flujo de usuario]

---

## 5. Lecciones Aprendidas y Concesiones (Trade-offs)

1. **Trade-off 1:** [e.g. Complejidad de crear archivos separados por Value Object vs. seguridad de tipado e inmutabilidad estricta].
2. **Trade-off 2:** [e.g. Caché en memoria inicial frente a latencia y estrategia de invalidación ante escrituras concurrentes].

---

## 6. Historial de Trazabilidad y Commits

### Historial de la Feature Branch (`feat/[US-XX-slug]`)

* `[hash]`: `test(acceptance): define gherkin scenarios for US-XX [expected red]`
* `[hash]`: `test(domain): add failing test for [concept] [red]`
* `[hash]`: `feat(domain): implement [concept] to pass test [green]`
* `[hash]`: `refactor(domain): clean up [concept] adhering to rules`
* `[hash]`: `docs(publication): add technical article for US-XX`

### Commit Final en `main` (Squash Merge)

* `pendiente` — `feat([context]): implement US-XX [slug] complete slice`
