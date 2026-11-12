---
id: agent-rules-workflows-and-git
aliases: []
tags: []
description: Workflows, pytest enforcement, conventional commits, and mandatory updates to Mermaid system map. Activate when finalizing tasks, writing tests, creating commits, or updating architecture diagrams.
trigger: model_decision
---

# 01 — Workflows, Verification & Git Directives

Este documento rige el ciclo de ejecución y los estándares de control de versiones en `ai-conversation-platform`. El agente debe acatar este flujo de trabajo de forma estricta.

---

## 1. El Bucle de Ejecución por Tarea (Execution Loop)

Para cada funcionalidad, refactor o slice asignado, el agente debe seguir este orden secuencial:

1. **Lectura de Especificación y Templates:**
   - Inspeccionar la spec activa en `.agent/specs/current/`.
   - Revisar las plantillas canónicas correspondientes en `.agent/templates/`.
2. **Implementación guiada por Contratos:**
   - Escribir código respetando los límites de capas definidos en `00-core-philosophy.md`.
3. **Verificación Automatizada (Barrera de Calidad):**
   - Ejecutar la suite de pruebas mediante comando:
     ```bash
     pytest tests/ -v
     ```
   - Si una prueba falla, entrar en ciclo de autocorrección. **Queda terminantemente prohibido modificar los tests para forzar que pasen si el cambio debilita las invariantes de negocio.**
4. **Sincronización del Diagrama Vivo (Mermaid):**
   - Antes de dar la tarea por finalizada, actualizar `.agent/architecture/system-map.mermaid.md`.
5. **Publicación Técnica (solo vertical slices):**
   - Consolidar y validar `docs/articles/ARTICLE-<NNN>-<slug>.md` según la §4.
6. **Reporte al Desarrollador:**
   - Presentar el resumen del cambio, el estado de los tests y el diff visual del diagrama actualizado.

---

## 2. Invariante del Diagrama Vivo (`system-map.mermaid.md`)

El archivo `.agent/architecture/system-map.mermaid.md` es la fuente viva de verdad visual del sistema.

### Reglas de Actualización:

- **Alta de Artefactos:** Si se crea una nueva entidad, comando, query, puerto, adaptador o router, DEBE agregarse el nodo correspondiente dentro de su `subgraph` de capa en el archivo Mermaid.
- **Relaciones:** Se deben trazar las flechas correspondientes:
  - Flecha continua (`-->`) para llamadas de orquestación (ej. `Router --> Handler`).
  - Flecha discontinua (`-.->`) para emisión de eventos (ej. `Entity -.-> DomainEvent`).
  - Flecha etiquetada (`-- Implementa -->`) para adaptadores que satisfacen puertos abstractos.
- **Consistencia:** Si un archivo es renombrado o eliminado, el nodo correspondiente en Mermaid debe ajustarse de inmediato.

---

## 3. Protocolo de Commits y Git

### Formato de Mensajes (Conventional Commits)

Los mensajes de commit deben seguir la convención:
`<tipo>(<alcance>): <descripción imperativa en minúsculas>`

- `feat(conversations)`: Nueva funcionalidad de dominio, aplicación o interfaz.
- `fix(outbox)`: Corrección de un fallo en la lógica o infraestructura.
- `test(conversations)`: Incorporación o mejora de casos de prueba.
- `refactor(persistence)`: Cambios de estructura sin alterar comportamiento externo.
- `docs(architecture)`: Actualización de diagramas, ADRs o especificaciones.

### Checkpoints Obligatorios Pre-Commit:

Un commit solo puede sugerirse o ejecutarse si:

1. `pytest` finaliza con código de salida `0` (100% verde).
2. No existen imports circulares ni violaciones de capas de `00-core-philosophy.md`.
3. El archivo `.agent/architecture/system-map.mermaid.md` refleja fielmente los artefactos del commit.
4. No se dejan archivos temporales, logs ni credenciales en el staged area.
5. Si el cambio es un vertical slice, su artículo técnico existe y pasa el gate de la §4.

---

## 4. Fase de Publicación Técnica (Vertical Slices)

Cada vertical slice (User Story, command o query) produce un artículo técnico. Los refactors y cambios de arquitectura NO generan artículo: se documentan en ADRs (`.agent/architecture/decisions/`).

1. **Creación:** al iniciar el slice, copiar `.agent/templates/ARTICLE_TEMPLATE.python.md` a `docs/articles/ARTICLE-<NNN>-<slug>.md` (NNN = siguiente número libre de 3 dígitos) y registrar la entrada en `docs/articles/README.md`.
2. **Redacción incremental:** §1-2 al definir contratos y diseño; §3 tras el dominio; §4 con salidas reales de `pytest`; §5-6 al refactor y commits. Idioma: español, identificadores en inglés.
3. **Gate (Definition of Done):** antes de sugerir el commit, verificar que:
   - No quedan placeholders `[...]`, salvo `Squash Commit en main: pendiente`.
   - Todos los paths citados existen en el repositorio.
   - Los bloques de resultados de §4 provienen de ejecuciones reales de `pytest`.
   Si el gate falla, no se sugiere ni ejecuta el commit.
4. **Commit:** `docs(publication): add technical article for US-XX` en la feature branch.
5. **Post-merge (opcional):** reemplazar `pendiente` por el hash del squash commit en `main`.

