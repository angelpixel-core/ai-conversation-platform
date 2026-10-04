# ADR 0012: Estandarización de Pipelines de CI/CD (GitHub Actions con Service Containers y Calidad Modular)

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `feat/infra-pipelines-and-repo-standardization` — Sección 4.1 de RFC 01

---

## 1. Contexto y Problemática

El pipeline de CI previo en `.github/workflows/ci.yml` presentaba limitaciones para garantizar la calidad enterprise de `ai-conversation-platform`:

1. **Ausencia de Pruebas de Integración Reales en CI:**
   - La suite de pruebas corría exclusivamente en modo `in_memory`, omitiendo la ejecución de tests reales contra Microsoft SQL Server 2022 y RabbitMQ 3.13.
   - Las migraciones relacionales de base de datos (`alembic upgrade head`) no eran validadas en un motor SQL Server real durante las ejecuciones de Pull Request.
2. **Falta de Validación Estricta de Artefactos de Documentación:**
   - La generación de esquemas OpenAPI 3.1.0 y páginas ReDoc no contaba con un paso dedicado de aserción sintáctica para asegurar la integridad de `public/openapi.json` antes del despliegue.
3. **Falta de Validación de Compilación de Imágenes Docker:**
   - El `Dockerfile` de producción no era construido ni validado en CI, permitiendo que cambios en dependencias o estructura rompieran la creación de la imagen sin ser detectados.

---

## 2. Decisión de Diseño

Se rediseña la arquitectura del pipeline en GitHub Actions estructurándola en **5 jobs modulares, altamente paralelos y con Service Containers oficiales**:

### 2.1. Topología Modular de 5 Jobs Paralelos

1. **`lint-and-format`:**
   - Ejecuta `ruff format --check src tests` y `ruff check src tests`.
   - Duración estimada: < 20 segundos.
2. **`static-analysis`:**
   - Ejecuta análisis estricto de tipos con `pyright`.
   - Ejecuta escaneo estático de seguridad AST con `bandit -r src -s B101`.
3. **`test-unit-and-integration`:**
   - Monta dos **Service Containers oficiales** en el runner:
     - `db`: `mcr.microsoft.com/mssql/server:2022-latest` con healthcheck `sqlcmd`.
     - `broker`: `rabbitmq:3-management-alpine` con healthcheck `rabbitmq-diagnostics ping`.
   - Aplica migraciones de base de datos con `alembic upgrade head` (creando y migrando `ChatbotDB` automáticamente).
   - Ejecuta la suite completa de pruebas unitarias y de integración (619 tests) con reporte de cobertura XML.
4. **`docs-validation`:**
   - Ejecuta `src.interfaces.cli.export_openapi`.
   - Valida la existencia y conformidad JSON de `public/openapi.json` (OpenAPI 3.1.0) y `public/index.html`.
   - Publica los artefactos como build output para inspección.
5. **`docker-build-and-push`:**
   - Se ejecuta condicionado a que los 4 jobs de análisis y pruebas finalicen exitosamente (`needs: [lint-and-format, static-analysis, test-unit-and-integration, docs-validation]`).
   - Utiliza Docker Buildx (`docker/setup-buildx-action@v3`) y `docker/build-push-action@v5`.
   - Implementa cache eficiente en GitHub Actions (`cache-from: type=gha`, `cache-to: type=gha,mode=max`).
   - Construye la imagen `chatbot-api:latest` validando la integridad del contenedor de producción.

### 2.2. Políticas de Concurrencia y Ramas

- **Concurrencia:** Se cancelan automáticamente builds obsoletos en ramas de trabajo al enviar commits consecutivos (`cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`).
- **Eventos:** Se dispara en `push` a ramas `main`, `development`, `feat/**` y `feature/**`, y en `pull_request` contra `main` y `development`.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Detección Temprana de Fallos (Shift-Left):** Fallos en esquemas relacionales SQL Server o topologías RabbitMQ se detectan inmediatamente en el PR antes de tocar entornos de staging o producción.
- **Validación Multi-Stage:** Cada dimensión de calidad (estilo, tipado, seguridad, tests, docs, docker) está aislada en su propio job, facilitando el diagnóstico rápido ante fallos.
- **Velocidad y Eficiencia:** La ejecución paralela de los jobs iniciales minimiza el tiempo total del pipeline aprovechando la concurrencia nativa de GitHub Actions.
