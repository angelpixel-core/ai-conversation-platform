# ADR 0018: Tipado Estático Estricto (Python 3.12+ / Pyright) y Estandarización de Docstrings Estilo Google

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `refactor/source-code-and-clean-arch-polish` — Sección 3 y Paso 5 de RFC 02

---

## 1. Contexto y Problemática

A medida que el proyecto `ai-conversation-platform` madura a través de los múltiples vertical slices y refactorizaciones de Clean Architecture / DDD, la consistencia en el tipado estático y la claridad en la documentación interna de código se vuelven vitales para la mantenibilidad, legibilidad del IDE y prevención de defectos en tiempo de compilación/análisis estático.

Durante la auditoría del RFC 02, se identificaron los siguientes puntos:

1. **Persistencia Residual de Tipos Legados de `typing`:**
   - En Python 3.12+, la sintaxis de unión por tubería (`A | B | None`) y el soporte de genéricos en colecciones integradas (`list[T]`, `dict[K, V]`, `set[T]`, `frozenset[T]`, `tuple[T, ...]`) reemplazan por completo a `typing.Union`, `typing.Optional`, `typing.List`, `typing.Dict`, `typing.Set` y `typing.Tuple`.
   - Ciertos módulos aún conservaban importaciones de `Set` y `Optional`.
2. **Nivel de Verificación en Pyright:**
   - La configuración de Pyright en `pyproject.toml` no explicitaba el modo de verificación estándar ni diagnósticos estrictos de detección temprana como redefinición de constantes, comprobaciones booleanas que siempre evalúan a verdadero, parámetros `self`/`cls` inconsistentes, etc.
3. **Heterogeneidad en la Documentación de Métodos de Negocio:**
   - Ciertas clases y handlers de caso de uso carecían de docstrings con estructura unificada, o no detallaban explícitamente los parámetros (`Args:`), valores de retorno (`Returns:`) y excepciones esperadas (`Raises:`).

---

## 2. Decisión de Diseño

Se aprueba y formaliza la estandarización de tipado estricto y documentación Google Style:

### 2.1. Eliminación Definitiva de Constructos Legados de `typing`

- Queda terminantemente prohibido el uso de `Union`, `Optional`, `List`, `Dict`, `Set`, `Tuple` provenientes del módulo `typing` en todo el código productivo de `src/`.
- Toda unión debe expresarse mediante el operador nativo `|` (ej. `TenantPolicyModel | None`, `str | int`).
- Toda colección debe tiparse con los tipos built-in en minúscula (ej. `frozenset[str]`, `list[Message]`, `dict[str, Any]`).
- Se mantiene el uso de tipos estándar modernos de `typing` donde no exista sustituto sintáctico en el lenguaje (`Any`, `TypeVar`, `Protocol`, `Self`, `Annotated`, `NoReturn`).

### 2.2. Configuración Estricta de Pyright (`pyproject.toml`)

Se establece en `pyproject.toml` el modo canónico:
```toml
[tool.pyright]
include = ["src", "tests"]
exclude = ["src/infrastructure/persistence/mssql/migrations"]
extraPaths = ["."]
venvPath = "."
venv = ".venv"
typeCheckingMode = "standard"
reportMissingTypeStubs = false
reportAssertAlwaysTrue = "error"
reportInvalidStringEscapeSequence = "error"
reportInvalidTypeVarUse = "error"
reportSelfClsParameterName = "error"
reportConstantRedefinition = "error"
reportDuplicateImport = "error"
```
*(Se mantiene `reportMissingTypeStubs = false` para aislar librerías de terceros sin `py.typed` como `pymssql` y `aio_pika`)*.

### 2.3. Estándar de Docstrings Estilo Google

Todas las entidades, agregados raíces, comandos/queries CQRS, adaptadores de infraestructura y endpoints HTTP deben contar con docstrings estructurados conforme al estándar Google:
1. **Resumen inicial:** Frase concisa en modo imperativo.
2. **`Args:`**: Nombre de cada parámetro tipado y su descripción semántica.
3. **`Returns:`**: Descripción del valor o DTO retornado.
4. **`Raises:`**: Catálogo exhaustivo de excepciones de dominio o aplicación que pueden ser emitidas durante la ejecución.

---

## 3. Consecuencias y Beneficios

1. **Tipado 100% Moderno y Elegante:** Sintaxis alineada a las capacidades nativas de Python 3.12+.
2. **Garantía Estática contra Regresiones:** El linter de tipos Pyright opera con reglas reforzadas, detectando errores de tipado de forma temprana.
3. **Autodocumentación y Soporte IDE:** Los desarrolladores y agentes reciben información contextual precisa sobre argumentos, contratos y excepciones directamente en popups del editor.
4. **Validación Continua:** La suite `tests/unit/test_typing_and_docstrings_conformance.py` audita programáticamente el AST para rechazar automáticamente cualquier reintroducción de constructos obsoletos.
