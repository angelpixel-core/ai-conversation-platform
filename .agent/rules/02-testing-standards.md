---
id: 02-testing-standards
aliases: []
tags: []
---

# 02 — Testing Taxonomy & Layer Verification Standards

Este documento define la taxonomía, convenciones y políticas de testing para el repositorio `ai-conversation-platform`. El agente debe acatar estas directivas sin excepciones.

---

## 1. Pirámide y Taxonomía de Testing

Las pruebas se organizan estrictamente fuera de `src/` bajo el directorio raíz `tests/`, distribuidas por alcance técnico:

```text
tests/
├── conftest.py                   <-- Fixtures globales y configuración de pytest
├── unit/                         <-- Sin I/O, sin red, sin BD, ejecución en ms
│   ├── domain/
│   │   └── test_*_entity.py
│   └── application/
│       └── test_*_command_handler.py
└── integration/                  <-- Verificación de adaptadores e I/O
    ├── infrastructure/
    │   └── test_*_repository.py
    └── api/
        └── test_*_router.py

```

---

## 2. Estándares por Capa

### A. Dominio (`tests/unit/domain/`)

- **Objetivo:** Probar invariantes de negocio, mutaciones de estado y emisión de eventos de dominio.
- **Reglas:**
- Prohibido cualquier tipo de mock de librerías externas.
- No usar asyncio ni fixtures complejas salvo generación de datos en memoria.
- Cada método de negocio debe contar con casos para el camino feliz (_happy path_) y para cada excepción controlada (`ValueError`, `DomainError`).
- Verificar que `pull_events()` contenga exactamente los eventos emitidos con sus cargas útiles completas.

### B. Aplicación (`tests/unit/application/`)

- **Objetivo:** Probar la orquestación del caso de uso en aislamiento.
- **Reglas:**
- Los puertos de persistencia (`*RepositoryPort`) y transaccionalidad (`UnitOfWorkPort`) deben suministrarse mediante **Fakes en memoria o Mocks de interfaz** (`unittest.mock.AsyncMock`).
- No levantar bases de datos ni servicios reales.
- Comprobar que el comando llame al repositorio con la entidad correcta y ejecute el commit en la unidad de trabajo.

### C. Infraestructura (`tests/integration/infrastructure/`)

- **Objetivo:** Garantizar que los adaptadores concretos satisfagan el contrato del puerto abstracto.
- **Reglas:**
- En adaptadores en memoria: validar inserción, recuperación por ID, paginación y manejo de entidades no encontradas.
- En adaptadores de base de datos futura (SQLAlchemy/Postgres): probar transacciones reales, rollback en fallo y persistencia efectiva.

### D. Interfaces HTTP / API (`tests/integration/api/`)

- **Objetivo:** Validar serialización, códigos de estado HTTP y contratos OpenAPI.
- **Reglas:**
- Usar `httpx.AsyncClient` con `ASGITransport(app=app)`.
- Probar validaciones de Pydantic: enviar payloads incompletos o inválidos y validar que devuelvan `422 Unprocessable Entity`.
- Probar respuestas exitosas: validar código HTTP exacto (`201 Created` para POST, `200 OK` para consultas).

---

## 3. Política de Mocks y Aislamiento

1. **Favorecer Fakes sobre Mocks:** Si existe una implementación en memoria (`InMemoryConversationRepositoryAdapter`), prefiera inyectarla en lugar de fabricar cadenas complejas de `mock.patch()`.
2. **Prohibido Mockear el Dominio:** Nunca mockear entidades de dominio ni value objects. Las entidades son instancias reales.
3. **Prohibido Parchear Rutas Internas:** Evitar `patch("src.application...import")`. En su lugar, inyecte las dependencias a través del constructor del handler o use el `container.py` para sobreescribir dependencias de prueba.

---

## 4. Convenciones de Nomenclatura y Estructura

- **Archivos de prueba:** `test_<artefacto_a_probar>.py`
- **Funciones de prueba:** Nombradas siguiendo el patrón:
  `test_<metodo_o_accion>__<condicion_o_escenario>__<resultado_esperado>`
- _Ejemplo:_ `test_create__with_valid_title__records_conversation_created_event()`
- _Ejemplo:_ `test_append_message__with_empty_content__raises_invalid_conversation_error()`

- **Estructura interna (Arrange-Act-Assert):**

```python
@pytest.mark.asyncio
async def test_handle__valid_command__persists_conversation_and_returns_id():
    # Arrange (Preparar datos y dependencias)
    repository = InMemoryConversationRepositoryAdapter()
    uow = InMemoryUnitOfWorkAdapter(repository)
    handler = CreateConversationCommandHandler(repository=repository, unit_of_work=uow)
    command = CreateConversationCommand(title="General Discussion")

    # Act (Ejecutar acción)
    result = await handler.handle(command)

    # Assert (Validar consecuencias)
    assert result.conversation_id is not None
    saved = await repository.get_by_id(result.conversation_id)
    assert saved is not None
    assert saved.title == "General Discussion"

```

---

## 5. Criterio de Aprobación para el Agente

- Ejecutar la suite con: `pytest`
- No se admite un commit o cierre de tarea con tests ignorados (`@pytest.mark.skip`) sin justificación explícita ni tests fallidos.
