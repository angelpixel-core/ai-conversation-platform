# RFC 01 — Estandarización de Infraestructura, Pipelines, Secretos y Especificación Cloud (Staging & Producción)

- **Estado:** Propuesto / En Revisión
- **Rama Asociada:** `feat/infra-pipelines-and-repo-standardization`
- **Ámbitos:** Monorepo Tooling, Makefiles, Docker Compose, CI/CD, Secrets Management, AWS Cloud Provisioning
- **Fecha:** Octubre 2026

---

## 1. Contexto y Objetivos

A lo largo del desarrollo de los Slices 1 al 10, la aplicación backend en `apps/chatbot/service/api` ha evolucionado hacia una arquitectura enterprise basada en **Clean Architecture**, **DDD**, **CQRS** y **Event-Driven Architecture**, requiriendo componentes específicos:

- **Base de Datos:** Microsoft SQL Server 2022 con transacciones ACID, aislamiento multi-tenant y migraciones vía Alembic.
- **Message Broker:** RabbitMQ 3.13 con exchange topics para mensajería asíncrona y Outbox Relay.
- **Observabilidad:** OpenTelemetry con contexto W3C distribuido (`traceparent`).
- **Orquestación Local:** Un stack compuesto por `chatbot_api`, `chatbot_worker`, `mssql_db` y `rabbitmq_broker`.

Sin embargo, existe una disparidad histórica entre el directorio raíz del monorepo (`./../../../../`) y la aplicación:

1. `infra/local/compose/compose.yaml` (en la raíz) aún contiene definiciones legadas con PostgreSQL y configuraciones no alineadas con la arquitectura actual de MSSQL + RabbitMQ + FastAPI.
2. Existen dos `Makefile` (`./../../../../Makefile` y `apps/chatbot/service/api/Makefile`) con comandos y variables de entorno que requieren sincronización y estandarización.
3. La gestión de secretos y variables de entorno (`.env`, `.env.example`, `.env.template`) necesita un estándar canónico unificado con validación estricta.
4. El aprovisionamiento en Cloud (`infra/provisioning/aws`) requiere una especificación formal de **Requerimientos Mínimos** e **Ideales** para los entornos de **Staging (Non-Prod)** y **Producción**.

---

## 2. Diagnóstico de Disparidades y Soluciones Propuestas

### 2.1. Docker Compose: Monorepo (`infra/local/compose`) vs Servicio Local (Resuelto en ADR 0010)

- **Situación Previa:**
  - `infra/local/compose/compose.yaml` definía un contenedor `db` con PostgreSQL 16 y un comando Django inexistente (`manage.py runserver`).
  - `apps/chatbot/service/api/docker-compose.yml` definía `mssql_db` (MSSQL 2022), `rabbitmq_broker` (RabbitMQ 3.13), `chatbot_api` y `chatbot_worker`.
- **Estandarización Implementada (ver [ADR 0010](../../../.agent/architecture/decisions/0010-monorepo-compose-and-local-infrastructure-standardization.md)):**
  - **Servicios Unificados:** 5 componentes coordinados por capacidad arquitectónica: `api` (FastAPI / Uvicorn), `worker` (Python Inferencia & Outbox Relay), `portal` (Next.js 14+), `db` (contenedor `chatbot_db`, MSSQL 2022) y `broker` (contenedor `chatbot_broker`, RabbitMQ 3.13 Management).
  - **Red Bridge Común:** `chatbot_net` (`driver: bridge`, `attachable: true`) para comunicación inter-servicio transparente y acoplamiento de contenedores independientes o de pruebas.
  - **Puertos Estándar de Host:**
    - `api`: `8000:8000` (FastAPI / Swagger UI en `/docs`).
    - `portal`: `3000:3000` (Next.js Web Portal).
    - `db`: `1433:1433` (Microsoft SQL Server).
    - `broker`: `5672:5672` (AMQP) y `15672:15672` (Management Dashboard).
  - **Volúmenes Persistentes Nombrados:** `chatbot_db_data` y `chatbot_broker_data`.
  - **Healthchecks Nativos:** `sqlcmd` para la base de datos, `rabbitmq-diagnostics ping` para el broker, y verificación HTTP en `/health` para la API.

### 2.2. Makefiles: Jerarquía y Nomenclatura

- **Makefile Raíz (`./../../../../Makefile`):**
  - Actúa como la fachada principal para desarrolladores y operadores.
  - Comandos estandarizados:
    - `make stack/up-build`: Levanta la infraestructura local completa.
    - `make stack/status`: Diagnóstico de salud de todos los contenedores.
    - `make test/all`: Ejecuta suites de pruebas completas en backend y frontend.
    - `make provision/nonprod/plan` y `make provision/prod/plan`: Enlace con Terraform.
- **Makefile de la Aplicación (`apps/chatbot/service/api/Makefile`):**
  - Específico para el ciclo de vida del desarrollador Python:
    - `make check-all`: Pipeline local rápido (`format-check`, `lint`, `typecheck`, `security`, `test`).
    - `make test`: Ejecución de pytest con pausa temporal controlada del worker para evitar contención de locks en MSSQL.
    - `make db/upgrade`: Migraciones de Alembic.
    - `make db/downgrade`: Reversión de migraciones de Alembic.
    - `make db/shell`: Consola interactiva SQLCMD conectada a `ChatbotDB`.
    - `make stack/status`: Diagnóstico de salud de los servicios Docker Compose.
    - `make docs-build`: Generación estática de OpenAPI y ReDoc.

### 2.3. Scripts de Soporte y Diagnóstico (`infra/tooling/scripts/`)

- **`db.sh` (`infra/tooling/scripts/db.sh`):**
  - Estandarizado para soporte nativo de Microsoft SQL Server 2022:
    - Comando `shell`: Invoca `/opt/mssql-tools18/bin/sqlcmd -S localhost -U "${MSSQL_USER:-sa}" -P "${MSSQL_SA_PASSWORD:-YourStrong!Passw0rd}" -C -d "${MSSQL_DB:-ChatbotDB}"`.
    - Comando `logs`: `run_compose logs -f db`.
- **`stack.sh` (`infra/tooling/scripts/stack.sh`):**
  - Incorpora subcomando `status`: Ejecuta `run_compose ps` para diagnosticar el estado del stack unificado en tiempo real.
  - Soporta parametrización de `STACK_COMPOSE_FILE` para interoperabilidad con compose local o monorepo.

---

## 3. Estándar de Variables de Entorno y Gestión de Secretos (Resuelto en [ADR 0011](../../../.agent/architecture/decisions/0011-standardized-environment-variables-and-secrets-management.md))

### 3.1. Niveles de Configuración

Se establece una matriz de 4 niveles para la configuración:

| Nivel | Ubicación | Control de Versiones | Propósito |
| :--- | :--- | :---: | :--- |
| **1. Plantilla Canónica** | [`.env.template`](../../../.env.template) / `config/examples/local.env` | **Sí (Git)** | Documentación exhaustiva con valores por defecto seguros, descripciones y tipos. |
| **2. Entorno Local** | `.env` / `.env.local` / `infra/environments/.local/project.env` | **No (.gitignore)** | Secretos locales del desarrollador, tokens de prueba y credenciales de contenedores locales. |
| **3. CI/CD** | GitHub Actions Secrets / Environment Secrets | **No (Cifrado)** | Credenciales de registry, tokens de análisis y claves de API de testing. |
| **4. Cloud (AWS)** | AWS Secrets Manager & SSM Parameter Store | **No (KMS)** | Secretos de producción con rotación automática (DB passwords, API keys de LLM, certificados). |

### 3.2. Reglas de Validación con Pydantic Settings

- [x] Toda variable se encuentra declarada y tipada en [`src/infrastructure/shared/config/settings.py`](../../../src/infrastructure/shared/config/settings.py) utilizando `pydantic-settings`.
- [x] Modelos modulares especializados: `AppSettings`, `DatabaseSettings`, `MessagingSettings`, `TenancySettings`, `GovernanceSettings`, `LlmSettings`.
- [x] Validadores estrictos (`@field_validator`):
  - Rango de puertos válidos (`1 <= port <= 65535`) para `API_PORT`, `DB_PORT` y `BROKER_PORT` (con alias `RABBITMQ_PORT`).
  - Nivel de log (`LOG_LEVEL`) validado contra niveles estándar de Python (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- [x] Principio **Fail-Fast** en arranque: `@model_validator(mode="after")` que comprueba que si se configuran drivers externos (`mssql` o `rabbitmq`), los parámetros requeridos no sean cadenas vacías.
- [x] Principio de Aislamiento Hexagonal: Queda terminantemente prohibido hacer `os.environ.get()` ad-hoc dentro de capas de Dominio o Aplicación; toda configuración se inyecta desde el Composition Root (`src/container.py` y `src/worker_container.py`).

---

## 4. Estandarización de Pipelines de CI/CD (Resuelto en [ADR 0012](../../../.agent/architecture/decisions/0012-github-actions-ci-cd-standardization-and-service-containers.md))

### 4.1. Workflows en GitHub Actions (`.github/workflows/`)

Se estructuran y ejecutan 5 jobs modulares y paralelos en `.github/workflows/ci.yml`:

- [x] **`lint-and-format`**:
  - `ruff format --check src tests`
  - `ruff check src tests`
- [x] **`static-analysis`**:
  - `pyright` (tipado estricto sin errores)
  - `bandit -r src -s B101` (escaneo de seguridad AST sin vulnerabilidades)
- [x] **`test-unit-and-integration`**:
  - **Service Containers oficiales:** `mcr.microsoft.com/mssql/server:2022-latest` (`1433`) y `rabbitmq:3-management-alpine` (`5672`/`15672`).
  - Ejecución de migraciones Alembic (`alembic upgrade head`).
  - Ejecución de la suite completa de pruebas (`pytest` con 619 tests y reporte XML de cobertura).
- [x] **`docs-validation`**:
  - Ejecución de `src.interfaces.cli.export_openapi`.
  - Validación de esquema OpenAPI 3.1.0 (`public/openapi.json`) y standalone HTML de ReDoc (`public/index.html`).
- [x] **`docker-build-and-push`**:
  - Verificación de compilación del `Dockerfile` multi-stage con Docker Buildx y cache en GitHub Actions (`type=gha`).

---

## 5. Matriz de Requerimientos de Infraestructura Cloud (Resuelto en [ADR 0013](../../../.agent/architecture/decisions/0013-cloud-infrastructure-requirements-and-provisioning-matrix.md))

Para la arquitectura en AWS gestionada con Terraform (`infra/provisioning/aws`) y GitOps con ArgoCD, se define y formaliza en **[ADR 0013](../../../.agent/architecture/decisions/0013-cloud-infrastructure-requirements-and-provisioning-matrix.md)** y en [`infra/provisioning/aws/README.md`](../../../../../../infra/provisioning/aws/README.md) la siguiente especificación comparativa:

### 5.1. Comparativa de Componentes: Mínimos vs. Ideales

- [x] **Topología de Red 3-Tier en AWS:** Aislamiento en 3 capas de subredes (`public`, `private_app`, `private_data`) a lo largo de 3 AZs.
- [x] **Paridad Estricta de RDBMS:** **Amazon RDS for SQL Server 2022** (Multi-AZ Always On en Producción; Single-AZ en Non-Prod).
- [x] **Paridad Estricta de Message Broker:** **Amazon MQ for RabbitMQ 3.13** (Cluster Multi-AZ con Quorum Queues en Producción; Single-Broker en Non-Prod).
- [x] **Almacenamiento de Documentos RAG:** **Amazon S3 Enterprise** con SSE-KMS, Versionado y Object Lock para cumplimiento.
- [x] **Gestión de Secretos:** **AWS Secrets Manager** con rotación y sincronización hacia EKS vía **External Secrets Operator (ESO)**.
- [x] **Seguridad Perimetral:** **AWS WAF v2** con OWASP Core Rule Set y Rate Limiting.
- [x] **Observabilidad y Telemetría:** **OpenTelemetry Collector DaemonSet** en EKS, AMP/AMG y CloudWatch Logs (retención 90 días + S3 Glacier).
- [x] **SLA y Resiliencia:** 99.95% de disponibilidad, RTO < 15 min, RPO < 5 min en Producción.

| Componente | Requerimientos Mínimos (Staging / Non-Prod) | Requerimientos Ideales (Producción Enterprise) |
| :--- | :--- | :--- |
| **Cómputo (K8s / Containers)** | **Amazon EKS 1.31** con 1 Managed Node Group:<br>- 2 nodos `t3.xlarge` o `t3a.xlarge`<br>- Auto-recovery estándar<br>- Single AZ o Multi-AZ básica | **Amazon EKS 1.31** con arquitectura Multi-AZ:<br>- Karpenter para autoscaling inteligente de pods<br>- Nodos `m6i.xlarge` / `c6i.xlarge` distribuidos en 3 AZs<br>- Pod Disruption Budgets y Topology Spread Constraints |
| **Base de Datos (RDBMS)** | **Amazon RDS for SQL Server 2022** (Web Edition o Standard):<br>- Instancia `db.t3.xlarge`<br>- Single-AZ con Storage GP3 (50 GB)<br>- Backups automáticos retención 7 días<br>- Cifrado KMS en reposo | **Amazon RDS for SQL Server 2022** (Enterprise / Standard):<br>- Despliegue **Multi-AZ con Always On Availability Groups**<br>- Instancia `db.r6i.2xlarge` (memoria optimizada)<br>- Storage GP3/IO2 provisionado con auto-scaling<br>- Read Replicas para queries de reportes y auditoría<br>- Backups continuos point-in-time (PITR) a 35 días |
| **Message Broker** | **Amazon MQ for RabbitMQ 3.13**:<br>- Despliegue Single-Broker `mq.m5.large`<br>- Durabilidad en disco estándar | **Amazon MQ for RabbitMQ 3.13**:<br>- **Cluster Multi-AZ (Active/Standby o 3-node quórum)**<br>- Quorum queues habilitadas para tolerancia a particiones de red<br>- Instancia `mq.m5.xlarge` con almacenamiento EBS optimizado |
| **Almacenamiento de Documentos (RAG)** | **Amazon S3 Standard**:<br>- Bucket para documentos y artefactos de conocimiento<br>- Cifrado SSE-S3 o SSE-KMS | **Amazon S3 con Lifecycle & Versioning**:<br>- Versionado inmutable y Object Lock (compliance audit)<br>- Cifrado obligatorio SSE-KMS con rotación anual de clave<br>- Intelligent-Tiering para reducir costos de almacenamiento |
| **Gestión de Secretos** | **AWS Systems Manager Parameter Store** (SecureString con KMS) para parámetros y secrets básicos. | **AWS Secrets Manager** con rotación automática de credenciales de base de datos y llaves de proveedores LLM. Integración con External Secrets Operator (ESO) en EKS. |
| **Red y Seguridad Perimetral** | - VPC con subnets públicas y privadas en 2 AZs<br>- 1 NAT Gateway (para contención de costos en staging)<br>- Security Groups estrictos con principio de mínimo privilegio | - VPC con subnets públicas, privadas y aisladas (Data Layer) en 3 AZs<br>- 3 NAT Gateways (alta disponibilidad por zona)<br>- **AWS WAF v2** en Application Load Balancer con reglas OWASP Core Rule Set y Rate Limiting agresivo |
| **Observabilidad y Auditoría** | - CloudWatch Logs básicos con retención de 14 días<br>- Métricas de CPU/Memoria en EKS y RDS | - **OpenTelemetry Collector** desplegado como DaemonSet en EKS<br>- Ingesta de trazas W3C en AWS X-Ray o Grafana Tempo<br>- Métricas en Amazon Managed Prometheus & Amazon Managed Grafana<br>- CloudWatch Logs con retención de 90 días y exportación a S3 Glacier para auditoría forense |
| **Disponibilidad y Resiliencia** | SLA objetivo: **99.5%**<br>RTO: 4 horas<br>RPO: 1 hora | SLA objetivo: **99.95%**<br>RTO: < 15 minutos (failover automático Multi-AZ)<br>RPO: < 5 minutos (zero data loss para transacciones comprometidas) |

---

## 6. Plan de Implementación de esta Rama

1. **Fase 1: Estandarización de Archivos y Nomenclaturas en `infra/` y Makefiles:**
   - Crear / actualizar `infra/local/compose/compose.yaml` alineado con el stack actual.
   - Sincronizar targets del `Makefile` de la raíz para delegar limpiamente en la API y el portal.
2. **Fase 2: Unificación de Variables de Entorno y Secretos:**
   - Generar `.env.template` exhaustivo y documentado.
   - Definir variables de staging y prod en `infra/environments/`.
3. **Fase 3: Verificación y Testing de Integración:**
   - Validar que `make stack/up-build` y `make test-happy-path` funcionen sin fricciones desde la raíz y desde el subdirectorio de la aplicación.
4. **Fase 4: Documentación y Merge:**
   - Documentar los cambios en el changelog de infra y preparar el PR de la rama.
