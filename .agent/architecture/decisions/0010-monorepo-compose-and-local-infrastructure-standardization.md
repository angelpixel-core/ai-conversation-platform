# ADR 0010: Estandarización de Docker Compose (Monorepo `infra/local/compose` vs Servicio Local) e Infraestructura Local

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `feat/infra-pipelines-and-repo-standardization` — Sincronización de Entornos de Ejecución Local y Orquestación

---

## 1. Contexto y Problemática

Durante las fases iniciales del proyecto (Slices 1 a 10), el desarrollo del backend se concentró en `apps/chatbot/service/api`, implementando una arquitectura empresarial completa:

- **Base de Datos Principal:** Microsoft SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`) con esquemas relacionales, transacciones ACID, aislamiento multi-tenant y migraciones gestionadas mediante Alembic.
- **Message Broker:** RabbitMQ 3.13 (`rabbitmq:3-management-alpine`) para mensajería asíncrona de eventos de dominio, Outbox Relay y distribución de carga hacia workers desacoplados.
- **API Backend:** FastAPI / Uvicorn exponiendo endpoints síncronos, SSE streaming, OpenAPI 3.1.0 y middlewares de observabilidad (OpenTelemetry W3C trace context).
- **Proceso Worker:** Worker asíncrono en Python (`python -m src.worker`) para procesamiento de inferencia y entrega garantizada de mensajes.
- **Portal Frontend:** Aplicación Next.js 14+ (`apps/chatbot/web/portal`) interactuando con la API y streaming.

Sin embargo, el directorio de orquestación de nivel monorepo (`infra/local/compose/compose.yaml` y scripts en `infra/tooling/scripts/`) mantenía una configuración legada basada en PostgreSQL 16 y un comando Django inexistente (`manage.py runserver`), generando:

1. **Fricción de Entrada:** Nuevos desarrolladores u operadores que ejecutan `make stack/up` desde la raíz iniciaban un contenedor de PostgreSQL que no es utilizado por el backend actual, fallando por falta de dependencias (MSSQL y RabbitMQ).
2. **Disparidad de Redes y Puertos:** Discrepancias entre los puertos de host (puertos `10001`, `10002`, `10003` en la raíz vs `8000`, `3000`, `1433`, `5672`/`15672` en el servicio local).
3. **Mantenimiento Duplicado:** Falta de un contrato claro entre la orquestación global del monorepo y la ejecución autónoma del backend.

---

## 2. Decisión de Diseño

Se adopta una unificación arquitectónica estricta para garantizar paridad total entre la ejecución global del monorepo y el servicio local:

### 2.1. Principio de Neutralidad Tecnológica y Servicios Canónicos

En coherencia con los principios de **Clean Architecture y Ports & Adapters**, los nombres de los servicios y contenedores en la topología de red de Docker Compose deben representar su **rol o capacidad arquitectónica**, evitando acoplarse al nombre comercial del software o proveedor:

1. **`db` (`chatbot_db`):**
   - Rol: Almacenamiento persistente relacional y transaccional ACID.
   - Imagen: `mcr.microsoft.com/mssql/server:2022-latest` (adaptador concreto MSSQL 2022).
   - Puerto host: `1433:1433`.
   - Healthcheck: `/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '${DB_PASSWORD}' -C -Q 'SELECT 1'`.
   - Persistencia: Volumen canónico `chatbot_db_data`.
2. **`broker` (`chatbot_broker`):**
   - Rol: Intermediario de mensajería asíncrona, colas y eventos de dominio (Message / Event Broker).
   - Imagen: `rabbitmq:3-management-alpine` (adaptador concreto RabbitMQ 3.13).
   - Hostname de red interna: `broker`.
   - Puertos: `5672:5672` (AMQP) y `15672:15672` (Management Console).
   - Healthcheck: `rabbitmq-diagnostics -q ping`.
   - Persistencia: Volumen canónico `chatbot_broker_data`.
3. **`api` (`chatbot_api`):**
   - Rol: Servidor HTTP REST & SSE streaming principal.
   - Build: `apps/chatbot/service/api/Dockerfile` (Python 3.12-slim).
   - Comando: `uvicorn src.main:app --host 0.0.0.0 --port 8000`.
   - Puerto host: `8000:8000` (configurable vía `${SERVICES_PORT:-8000}`).
   - Healthcheck: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"`.
   - Dependencias de salud: `db` y `broker` en condición `service_healthy`.
4. **`worker` (`chatbot_worker`):**
   - Rol: Procesamiento en segundo plano, inferencia asíncrona y Outbox Relay.
   - Build: `apps/chatbot/service/api/Dockerfile`.
   - Comando: `python -m src.worker`.
   - Dependencias de salud: `db` y `broker` en condición `service_healthy`.
5. **`portal` (`chatbot_portal`):**
   - Rol: Interfaz de usuario web para operadores y usuarios finales.
   - Build: `apps/chatbot/web/portal/Dockerfile` (Node 22-alpine).
   - Puerto host: `3000:3000` (configurable vía `${WEB_PORT:-3000}`).
   - Variable de enlace: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

### 2.2. Red Unificada

Todos los servicios se interconectan mediante una red bridge compartida denominada `chatbot_net`.

### 2.3. Herramientas y Scripts de Soporte (`infra/tooling/scripts/`)

- `db.sh shell`: Actualizado para invocar `/opt/mssql-tools18/bin/sqlcmd` interactivo en el contenedor `db`.
- `stack.sh status`: Permite inspeccionar la salud de los 5 contenedores en tiempo real.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Paridad 100%:** `make stack/up-build` desde la raíz o desde la API ejecuta exactamente la misma infraestructura.
- **Zero-Friction Onboarding:** No se requieren pasos manuales para cambiar entre motores de bases de datos.
- **Aislamiento y Conectividad:** El portal frontend en Next.js se conecta inmediatamente con el backend y el broker para streaming y approvals.

### Negativas / Mitigaciones

- MSSQL 2022 requiere mayor asignación de memoria que PostgreSQL (mínimo recomendado: 2 GB de RAM dedicados en Docker Desktop). Esto se documenta claramente en los requisitos de sistema de los READMEs.
