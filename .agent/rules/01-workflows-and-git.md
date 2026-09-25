---
id: agent-workflows-and-git
aliases: []
tags: []
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
5. **Reporte al Desarrollador:**
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
