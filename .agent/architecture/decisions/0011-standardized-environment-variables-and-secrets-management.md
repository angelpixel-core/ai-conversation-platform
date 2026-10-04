# ADR 0011: Estandarización de Variables de Entorno, Gestión de Secretos y Validación Tipada (Pydantic Settings)

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-10-03
- **Autores:** Core Architecture Team
- **Contexto:** Rama `feat/infra-pipelines-and-repo-standardization` — Sección 3 de RFC 01

---

## 1. Contexto y Problemática

A medida que `ai-conversation-platform` creció a través de los Slices 1 al 10 incorporando persistencia relacional en Microsoft SQL Server 2022, mensajería asíncrona distribuida con RabbitMQ 3.13, observabilidad OpenTelemetry W3C, aislamiento multi-tenant y gateway de inferencia LLM, la gestión de configuración presentaba los siguientes riesgos:

1. **Fragmentación y Falta de Canonicidad:**
   - Existía un archivo `.env.example` embrionario con solo 3 variables (`APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL`), dejando indocumentadas más de 20 variables críticas de persistencia, mensajería, seguridad y observabilidad.
   - En el monorepo raíz, `config/examples/local.env` aún mantenía variables heredadas de PostgreSQL y un stack anterior, creando confusión para operadores y nuevos desarrolladores.
2. **Ausencia del Principio Fail-Fast en Arranque:**
   - La falta de validadores tipados estrictos en puertos y niveles de configuración permitía que la aplicación arrancara con puertos inválidos (ej. negativos o superiores a 65535) o valores de log erróneos, fallando tardíamente en tiempo de ejecución.
3. **Invariantes de Clean Architecture:**
   - Para cumplir estrictamente con Clean Architecture y DDD, las capas de Dominio y Aplicación deben permanecer completamente desacopladas del entorno operativo. Queda prohibido el uso de `os.environ.get()` o accesos globales directos a variables de sistema en dichas capas.

---

## 2. Decisión de Diseño

Se adopta una política de configuración basada en **4 Niveles Jerárquicos**, **Zero-Trust de Secretos** y **Validación Tipada Temprana**:

### 2.1. Matriz de 4 Niveles de Configuración

| Nivel | Ubicación | Control de Versiones | Propósito |
| :--- | :--- | :---: | :--- |
| **1. Plantilla Canónica** | `.env.template` / `config/examples/local.env` | **Sí (Git)** | Documentación exhaustiva con valores por defecto seguros, descripciones y tipos válidos. |
| **2. Entorno Local** | `.env` / `infra/environments/.local/project.env` | **No (.gitignore)** | Secretos locales del desarrollador, contraseñas de contenedores locales y tokens de prueba. |
| **3. CI/CD** | GitHub Actions Secrets / Environment Secrets | **No (Cifrado)** | Credenciales de registry, tokens de análisis y claves de API de testing en pipelines. |
| **4. Cloud (AWS)** | AWS Secrets Manager & SSM Parameter Store | **No (KMS)** | Secretos de producción con rotación automática (passwords de DB, API keys de LLM, certificados). |

### 2.2. Plantilla Canónica Exhaustiva (`.env.template`)

- [x] Se introduce el archivo canónico [`.env.template`](file:///apps/chatbot/service/api/.env.template) estructurado en 6 secciones funcionales:
  1. *Application & Core Server*: `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`, `API_HOST`, `API_PORT`.
  2. *Database Persistence*: `PERSISTENCE_DRIVER`, `DB_SERVER`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DATABASE_URL`.
  3. *Asynchronous Messaging Broker*: `MESSAGING_DRIVER`, `BROKER_URL`, `BROKER_HOST`, `BROKER_PORT`, `BROKER_USER`, `BROKER_PASSWORD`, topología canónica `BROKER_*` (con alias `RABBITMQ_*` para retrocompatibilidad).
  4. *Multi-Tenancy & Policy Engine*: `ENABLE_TENANT_MIDDLEWARE`, `DEFAULT_TENANT_ID`.
  5. *Enterprise AI Governance & Observability*: `ENABLE_OPENTELEMETRY`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`.
  6. *LLM Inference Gateway*: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_TIMEOUT_SECONDS`.
- [x] Se alinea [`.env.example`](file:///apps/chatbot/service/api/.env.example) para ofrecer una copia de arranque rápido local (`cp .env.example .env`).

### 2.3. Modelado Tipado y Fail-Fast en Pydantic Settings

- [x] Se formalizan modelos modulares en [settings.py](file:///src/infrastructure/shared/config/settings.py):
  - `AppSettings`: Controles de ciclo de vida HTTP y logging con validador de niveles estándar (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) y rango de puertos (1-65535).
  - `DatabaseSettings`: Validador de puerto MSSQL y método seguro `get_database_url()`.
  - `MessagingSettings`: Estandarización canónica a `BROKER_*` (con `validation_alias=AliasChoices(...)` y properties para retrocompatibilidad transparente), validador de puerto AMQP y métodos `get_broker_url()` / `get_rabbitmq_url()`.
  - `GovernanceSettings`: Parámetros de telemetría y OTLP endpoint.
  - `LlmSettings`: Configuración de proveedores LLM y timeouts.
- [x] **Fail-Fast Driver Validation:** Validador de modelo (`@model_validator(mode="after")`) que asegura que si `PERSISTENCE_DRIVER == "mssql"` o `MESSAGING_DRIVER == "rabbitmq"`, los parámetros esenciales de conexión no estén vacíos antes de inicializar el composition root.
- [x] **Preservación de Valores In-Memory por Defecto:** Los valores por defecto de fábrica se mantienen en `in_memory` para permitir que los 611 tests unitarios se ejecuten sin dependencias externas en menos de 10 segundos.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Zero-Friction & Self-Documenting:** Cualquier desarrollador u operador tiene visibilidad inmediata de todas las variables del sistema en `.env.template`.
- **Fail-Fast:** Los errores de configuración se detectan al importar la configuración o arrancar el contenedor, evitando excepciones oscuras en tiempo de ejecución.
- **Seguridad Garantizada:** Los archivos `.env` y `.env.local` están estrictamente ignorados por Git, evitando la fuga inadvertida de credenciales a repositorios públicos o compartidos.

### Mitigaciones

- **Sincronización Continua:** Al agregar una nueva capacidad vertical que requiera una variable de entorno, el agente y los desarrolladores deben actualizar simultáneamente `.env.template`, `settings.py` y los tests de configuración correspondientes.
