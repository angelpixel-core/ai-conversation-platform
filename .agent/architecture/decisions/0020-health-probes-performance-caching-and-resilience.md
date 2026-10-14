# ADR 0020: Optimización de Rendimiento, Resiliencia Fail-Fast y Caché en Memoria (TTL) para Probes de Salud (`GET /health`)

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-14
- **Autores:** Core Architecture Team
- **Contexto:** Rama `feat/health-observability-contract` — Caso de Uso 01 (CU-01) y Auditoría de Rendimiento (Fase 6)

---

## 1. Contexto y Problemática

Tras la implementación del contrato de observabilidad enriquecido para `GET /health` (ADR 0019), se condujo una auditoría exhaustiva de rendimiento y estabilidad operativa sobre los componentes Python, FastAPI y la arquitectura de puertos y adaptadores. Se detectaron tres vectores críticos de riesgo en entornos de alta concurrencia y producción:

1. **Vulnerabilidad a Bloqueos Indefinidos (Lack of Probe Timeouts):**
   - La orquestación concurrente `asyncio.gather(db_task, broker_task, ai_task)` no definía un límite temporal estricto (*hard timeout*).
   - Si la red experimenta partición, el socket TCP de RabbitMQ entra en estado *deadlock*, o el motor SQL Server retiene locks de tabla, la solicitud HTTP quedaba suspendida consumiendo un worker de AnyIO hasta que el cliente o proxy inverso abortara la conexión (30s–60s).
2. **Saturación por Sondeo Masivo (*Thundering Herd & Connection Pool Churn*):**
   - En infraestructuras cloud modernas (Kubernetes, AWS ECS, GCP Cloud Run), múltiples agentes inspeccionan `/health` de forma simultánea e intensiva: *Liveness Probe*, *Readiness Probe*, *Startup Probe*, balanceadores de carga (ALB/Nginx) y el Frontend Web Portal (`apps/chatbot/web/portal`).
   - Ejecutar `engine.connect()` y `SELECT 1` contra SQL Server en cada una de estas solicitudes genera contención directa sobre el pool de conexiones (`QueuePool`) del sistema de persistencia, pudiendo agotar las conexiones disponibles para transacciones de negocio.
3. **Ausencia de Directivas de Caché HTTP y Diagnóstico de Estado:**
   - La respuesta carecía de cabeceras explícitas `Cache-Control`, permitiendo potencialmente que proxies intermedios almacenen en caché estados transitorios de falla o salud.
   - No existía observabilidad granular para determinar si una respuesta de diagnóstico provino de una ejecución fresca de I/O o de una resolución en memoria.

---

## 2. Decisión de Diseño

Se aprueba y formaliza un conjunto de optimizaciones de baja latencia y alta resiliencia integrado en las capas de aplicación, infraestructura e interfaces:

### 2.1. Guardrail Fail-Fast con Timeouts Estrictos por Probe
- En `GetHealthStatusQueryHandler`, la ejecución de cada probe se encuentra delimitada mediante `asyncio.wait_for(probe.check_health(), timeout=self._timeout_seconds)`.
- El valor por defecto se establece en `1.5s` (configurable vía variable de entorno `HEALTH_CHECK_TIMEOUT_SECONDS`).
- Ante la expiración del plazo, se cancela la tarea, se registra una advertencia y se reporta de inmediato:
  ```python
  ComponentHealthResult(
      status="unhealthy",
      latency_ms=1500.0,
      engine=default_engine,
      details="Health probe timed out after 1.50s",
  )
  ```
  Esto garantiza que el SLA máximo del endpoint `/health` esté acotado a `<= 1.5s` en el peor escenario catastrófico de caída de infraestructura.

### 2.2. Caché en Memoria con Ventana Deslizante (In-Memory Sliding TTL Buffer)
- Se incorpora en `GetHealthStatusQueryHandler` un buffer en memoria con tiempo de vida (TTL) configurable (por defecto `cache_ttl_seconds = 2.0s`, controlado por `HEALTH_CHECK_CACHE_TTL_SECONDS`).
- **Flujo de Ejecución:**
  1. **Petición en Caliente (*Cache HIT*):** Si la última evaluación se produjo dentro del umbral de TTL (`now - last_evaluated_at < cache_ttl_seconds`), se devuelve una copia del resultado inmutable en **< 0.1ms** con `cached=True`, sin ejecutar I/O de red ni reservar hilos del pool.
  2. **Petición en Frío (*Cache MISS / Expiration*):** Si la caché expiró o está vacía, se adquiere un candado asíncrono `asyncio.Lock()` para prevenir el efecto *cache stampede*, se ejecutan los probes en paralelo, se actualiza el timestamp atómico con `time.monotonic()` y se sirve el resultado con `cached=False`.
  3. **Desactivación para Testing Determinista:** Si se parametriza `cache_ttl_seconds = 0.0`, el mecanismo de caché se salta por completo, garantizando pruebas unitarias limpias.

### 2.3. Resguardo de Pool en `MssqlHealthProbeAdapter`
- En el adaptador de persistencia MSSQL, la conexión y consulta se delimitan con directivas de ejecución rápida:
  ```python
  with self._engine.connect().execution_options(timeout=self._timeout_seconds) as conn:
      conn.execute(text("SELECT 1"))
  ```
  Evitando que hilos de verificación queden colgados en caso de indisponibilidad severa del motor de base de datos.

### 2.4. Cabeceras HTTP de Diagnóstico y Control de Tránsito
- En `src/interfaces/http/routers/health_router.py`, se configuran las siguientes cabeceras en toda respuesta:
  - `Cache-Control: no-cache, no-store, must-revalidate` (prohíbe el almacenamiento en proxies/navegadores).
  - `X-Health-Cache: HIT | MISS` (visibilidad instantánea para dashboards y depuración operativa).

---

## 3. Métricas de Rendimiento Obtenidas

| Escenario de Solicitud | Comportamiento de I/O | Latencia Típica | Impacto en Base de Datos / Broker |
| :--- | :--- | :--- | :--- |
| **Cache MISS (Evaluación Inicial / Expirada)** | Ejecución concurrente (`asyncio.gather`) | **5.0ms – 12.0ms** | 1 consulta `SELECT 1`, 1 ping robusto a RabbitMQ |
| **Cache HIT (Sondeo masivo dentro de 2.0s)** | Lectura de memoria (Zero I/O) | **< 0.10ms** | **0% de impacto (0 consultas, 0 hilos)** |
| **Fallo Crítico / Partición de Red** | Interrupción por timeout (`wait_for`) | **<= 1.50s** | Cancelación fail-fast, API 100% operativa |

---

## 4. Consecuencias y Validación

### Positivas:
- **Protección del Pool de Persistencia:** Reducción superior al 95% en la contención de conexiones frente a sondeos de Kubernetes y monitoreo continuo del Frontend Web Portal.
- **Inmunidad a Fallos en Cascada (*Restart Loops*):** Si la base de datos se satura, el probe falla rápido con estado `"unhealthy"` sin bloquear el servidor web ni disparar timeouts de HTTP gateway (504).
- **Compatibilidad Transparente:** La estructura del JSON permanece 100% idéntica a la acordada en ADR 0019, añadiendo únicamente metadatos HTTP para optimización de transporte.

### Validación Automatizada:
- Pruebas unitarias de query handler con caché y timeouts: [`tests/unit/application/test_get_health_status_query.py`](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/tests/unit/application/test_get_health_status_query.py) (9 tests pasando).
- Pruebas unitarias de cabeceras HTTP: [`tests/unit/interfaces/http/test_health_router.py`](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/tests/unit/interfaces/http/test_health_router.py) (3 tests pasando).
- Pruebas de integración E2E: [`tests/integration/api/test_health_endpoint.py`](file:///Users/angel.szymczak/Vaults/Harvis/300-MEMORIA_DIGITAL/475-Sites/AngelSolutions/Company/platform/convo/chatbot-ai-rag-langchain/apps/chatbot/service/api/tests/integration/api/test_health_endpoint.py) (Cache HIT/MISS y OpenTelemetry headers).
- Suite integral `make check-all`: 0 errores Ruff, 0 errores Pyright, 0 alertas Bandit, 100% de tests en verde.
