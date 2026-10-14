# ADR 0019: Contrato Enriquecido de Observabilidad de Salud (`GET /health`), Puertos de Diagnóstico y Desacoplamiento CQRS

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-14
- **Autores:** Core Architecture Team
- **Contexto:** Rama `feat/health-observability-contract` — Caso de Uso 01 (CU-01) y alineación con Frontend Web Portal (`apps/chatbot/web/portal`)

---

## 1. Contexto y Problemática

El endpoint de diagnóstico `GET /health` de la API de conversación operaba históricamente como un stub rudimentario definido de forma inline en `src/interfaces/http/api.py`:

```python
def _register_health_routes(app: FastAPI) -> None:
    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}
```

Este enfoque presentaba las siguientes deficiencias arquitectónicas y operativas:

1. **Insuficiencia de Diagnóstico para Clientes Web y Orquestadores:**
   - El Frontend Web Portal (`apps/chatbot/web/portal`), siguiendo el Caso de Uso 01 (CU-01) definido en `docs/frontend_portal_use_cases.md`, requiere inspeccionar el estado individual y la latencia en milisegundos de cada subsistema crítico (`database`, `broker`, `ai_engine`).
   - Una respuesta binaria `{"status": "ok"}` no permite detectar degradación de conexiones a SQL Server, demoras en el broker de mensajería RabbitMQ o indisponibilidad del motor de inferencia LLM.
2. **Violación de Clean Architecture y CQRS:**
   - La lógica de inspección estaba acoplada al framework web `FastAPI` sin una abstracción de aplicación (`QueryHandler`) ni puertos conducidos (`Driven Ports`).
   - No existía el router modular previsto en `STRUCTURE.md` (`src/interfaces/http/routers/health_router.py`).
3. **Falta de Trazabilidad y Tipado Estricto:**
   - El endpoint carecía de esquemas Pydantic v2 formales, soporte para exclusión de valores nulos y cobertura automatizada bajo observabilidad W3C TraceContext.

---

## 2. Decisión de Diseño

Se aprueba y formaliza la arquitectura completa para diagnósticos de salud mediante el patrón **Ports & Adapters (Hexagonal)** y **CQRS**, articulada en las siguientes capas:

### 2.1. Capa de Aplicación: Puerto Conducido y Query Handler CQRS

1. **Puerto Conducido `HealthProbePort` y Value Object `ComponentHealthResult`:**
   - Ubicación: `src/application/shared/ports/health_probe_port.py`.
   - `HealthStatus = Literal["healthy", "unhealthy", "degraded"]`.
   - Value Object inmutable `ComponentHealthResult`:
     - `status: HealthStatus`
     - `latency_ms: float`
     - `engine: str | None = None`
     - `details: str | None = None`
   - Interfaz abstracta:
     ```python
     class HealthProbePort(ABC):
         @abstractmethod
         async def check_health(self) -> ComponentHealthResult:
             ...
     ```

2. **Query y QueryHandler CQRS Concurrente:**
   - Ubicación: `src/application/shared/queries/get_health_status.py`.
   - `GetHealthStatusQuery`: DTO inmutable de consulta.
   - `HealthStatusResult`: DTO inmutable con estado agregado (`status`, `version`, `database`, `broker`, `ai_engine`).
   - `GetHealthStatusQueryHandler`: Orquesta la ejecución concurrente y no bloqueante de todos los probes mediante `asyncio.gather(db_task, broker_task, ai_task)`.
   - Algoritmo de agregación resiliente: Si algún probe falla con excepción no controlada, se captura de inmediato asignando `status="unhealthy"`, evitando que el endpoint `/health` colapse ante caídas de infraestructura.

### 2.2. Capa de Infraestructura: Adaptadores Conducidos (Driven Adapters)

Se implementan adaptadores específicos para entornos de producción y pruebas:

1. **Base de Datos (Persistence):**
   - `MssqlHealthProbeAdapter` (`src/infrastructure/persistence/mssql/mssql_health_probe_adapter.py`): Ejecuta ping `SELECT 1` sobre el `Engine` SQLAlchemy en un hilo separado con `anyio.to_thread.run_sync`, midiendo latencia real de round-trip y reportando `engine="mssql"`.
   - `InMemoryDatabaseHealthProbeAdapter` (`src/infrastructure/persistence/in_memory/in_memory_database_health_probe_adapter.py`): Probe ligero en memoria para tests y ejecución local desacoplada.
2. **Message Broker (Messaging):**
   - `RabbitMQHealthProbeAdapter` (`src/infrastructure/messaging/rabbitmq/rabbitmq_health_probe_adapter.py`): Inspecciona la robust connection de `aio-pika`, midiendo latencia de ping y reportando `engine="rabbitmq"`.
   - `InMemoryBrokerHealthProbeAdapter` (`src/infrastructure/messaging/in_memory/in_memory_broker_health_probe_adapter.py`): Probe en memoria para pruebas y desarrollo.
3. **Motor de IA (AI Engine):**
   - `AiEngineHealthProbeAdapter` (`src/infrastructure/llm/ai_engine_health_probe_adapter.py`): Valida disponibilidad del cliente LLM / catálogo de modelos. Reporta `engine=None` de manera intencional para coincidir exactamente con el contrato solicitado por el cliente web.

### 2.3. Capa de Interfaces: DTOs Pydantic v2 y Router Modular

1. **Esquemas de Transporte (`src/interfaces/http/health_schemas.py`):**
   - `ComponentHealthSchema`: `status`, `latency_ms`, `engine: str | None = None`.
   - `HealthChecksSchema`: DTO compuesto conteniendo `database`, `broker` y `ai_engine`.
   - `HealthCheckResponse`: DTO raíz con `status`, `version` y `checks`.
2. **Router Modular (`src/interfaces/http/routers/health_router.py`):**
   - Fábrica `create_health_router(health_handler: GetHealthStatusQueryHandler) -> APIRouter`.
   - Decorador `@router.get("/health", response_model=HealthCheckResponse, response_model_exclude_none=True)`.
   - La directiva `response_model_exclude_none=True` garantiza que campos opcionales omitidos (como `engine` en `ai_engine`) no se serialicen como `"null"` sino que no figuren en el payload JSON.
3. **Desacoplamiento de `build_api` y Composition Root (`src/container.py`):**
   - Se erradica la función privada `_register_health_routes(app)` de `api.py`.
   - El router de salud se inyecta y monta de forma idéntica a los demás driver routers (`conversations_router`, `governance_router`, etc.).

---

## 3. Contrato de Datos Formal (JSON Schema)

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 8.0,
      "engine": "mssql"
    },
    "broker": {
      "status": "healthy",
      "latency_ms": 4.0,
      "engine": "rabbitmq"
    },
    "ai_engine": {
      "status": "healthy",
      "latency_ms": 32.0
    }
  }
}
```

---

## 4. Consecuencias y Validación

### Positivas:
- **Observabilidad en Tiempo Real:** El Frontend Portal (`SystemStatusPill`) y sistemas de monitoreo pueden diagnosticar degradaciones puntuales de infraestructura sin consultar logs forenses.
- **Rendimiento Óptimo:** Los probes se ejecutan en paralelo con `asyncio.gather`, garantizando que el tiempo total de respuesta sea igual al componente más lento y no a la suma secuencial.
- **Resiliencia Extrema:** Fallos imprevistos de red o timeouts son absorbidos con estado `"unhealthy"` y detalle informativo en el JSON sin lanzar errores HTTP 500 no controlados.
- **Cumplimiento de Clean Architecture:** 100% de alineación con CQRS y reglas `00-core-philosophy.md`.

### Validación Automatizada:
- Pruebas unitarias de query handler: `tests/unit/application/test_get_health_status_query.py` (5 pruebas).
- Pruebas unitarias de router HTTP: `tests/unit/interfaces/http/test_health_router.py` (2 pruebas).
- Pruebas de integración con middlewares: `tests/integration/api/test_health_endpoint.py`.
- Suite E2E de walkthrough en vivo: `tests/integration/test_walkthrough_happy_path.py` (Paso 1).
- Barrera de calidad `make check-all`: 0 errores Ruff, 0 errores Pyright, 0 vulnerabilidades Bandit, 666 pruebas pasando en verde.
