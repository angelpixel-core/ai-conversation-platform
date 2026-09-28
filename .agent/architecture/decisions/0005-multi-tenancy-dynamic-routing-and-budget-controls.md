# ADR 0005: Aislamiento Multi-Tenant, Enrutamiento Dinámico de Modelos y Control Presupuestario Atómico

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-28
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 6 — Multi-Tenant Policy Engine, Dynamic Model Routing & Cost Budgets

---

## 1. Contexto y Problemática

Al evolucionar la plataforma conversacional hacia un modelo SaaS Enterprise multi-inquilino (*Multi-Tenant*), surgen desafíos críticos en escalabilidad, seguridad, gobernanza financiera y disponibilidad:

1. **Riesgo de Fuga de Datos y Contaminación Cruzada (*Data Leakage / Cross-Tenant Pollution*):**
   - En una infraestructura compartida, una consulta mal filtrada o la omisión accidental de una cláusula `WHERE` puede exponer conversaciones, mensajes o historiales confidenciales del *Tenant A* hacia el *Tenant B*.
2. **Condiciones de Carrera y Sobregiro en Concurrencia (*Double-Spending / Race Conditions*):**
   - Cuando múltiples usuarios o procesos de un mismo tenant disparan peticiones concurrentes de inferencia LLM, las consultas tradicionales de tipo `SELECT balance ... UPDATE balance` sin bloqueo transaccional permiten que dos hilos lean el mismo saldo antes de actualizarlo, provocando saldo negativo o ejecución no autorizada que supera el presupuesto financiero contratado.
3. **Dependencia Rígida de Proveedores LLM y Costos Descontrolados (*Vendor Lock-in & Unpredictable Costs*):**
   - El enrutamiento estático hacia un único proveedor de IA genera cuellos de botella cuando dicho proveedor sufre degradación de latencia o *rate limits* (HTTP 429). Asimismo, no todos los tenants requieren modelos de razonamiento de alto costo para consultas triviales; se precisa un enrutador dinámico que optimice costo vs. latencia según la política contractual del tenant.
4. **Propagación del Contexto Asíncrono en Concurrencia Estructurada:**
   - La plataforma utiliza **AnyIO** (`create_task_group`) y workers asíncronos desacoplados sobre **RabbitMQ**. El identificador del inquilino (`tenant_id`) debe propagarse de forma transparente y segura entre capas sin riesgo de fuga entre hilos ni pérdida de contexto en tareas hijas.

---

## 2. Decisión de Diseño

Se adopta una solución integral basada en Clean Architecture, DDD, CQRS y bloqueo transaccional pesimista sobre **Microsoft SQL Server (MSSQL)**:

### 2.1. Estrategia de Aislamiento Multi-Tenant: Base de Datos Compartida con Discriminador Lógico y Defensa en Profundidad

Se evalúan tres enfoques arquitectónicos:
- *Database-per-Tenant:* Máximo aislamiento, pero prohibitivo en coste operativo, migraciones y pool de conexiones para cientos de tenants.
- *Schema-per-Tenant:* Complejidad elevada en migraciones DDL de MSSQL y sobrecarga de metadatos.
- **Shared Database con Columna Discriminadora (`tenant_id`) e Índices Compuestos (Seleccionado):**
  - Todas las tablas principales (`conversations`, `messages` vía cascada, `audit_logs`, `outbox_messages`, `stream_buffer_chunks`) incorporan la columna `tenant_id: str = Field(index=True, max_length=64, nullable=False)`.
  - Se establecen índices compuestos en MSSQL: `(tenant_id, id)` y `(tenant_id, created_at)` para optimizar el plan de ejecución y garantizar consultas inmediatas indexadas por tenant.
  - **Defensa en profundidad:** Las consultas de repositorio exigen explícitamente el `tenant_id` como argumento mandatorio, y adicionalmente se implementa un hook / filtro contextual en el adaptador SQLModel/SQLAlchemy (`with_loader_criteria`) como red de seguridad.

### 2.2. Control Presupuestario Atómico con Bloqueos Pesimistas en MSSQL (`WITH (ROWLOCK, UPDLOCK)`)

Para prevenir sobregiros financieros ante ráfagas concurrentes:
1. **Reserva en Dos Fases (Reserve & Settle):**
   - **Fase de Reserva (`ReserveQuotaCommand`):** Antes de autorizar la inferencia y encolar el evento en el Outbox, se valida el saldo del inquilino y se reserva un monto estimado en tokens/USD.
   - **Fase de Liquidación (`SettleQuotaCommand`):** Una vez concluida la inferencia en el Worker, se calcula el consumo real de tokens a partir de los metadatos del proveedor LLM y se liquida la diferencia (reembolso del remanente o débito adicional).
2. **Bloqueo Pesimista en Transacción:**
   - En `MssqlTenantRepository.reserve_budget()`, la lectura del registro de balance se realiza con la directiva T-SQL:
     ```sql
     SELECT * FROM tenants WITH (ROWLOCK, UPDLOCK) WHERE id = :tenant_id
     ```
   - `ROWLOCK` restringe el bloqueo exclusivamente a la fila del tenant involucrado, evitando bloqueos a nivel de página o tabla.
   - `UPDLOCK` adquiere un bloqueo de actualización inmediato durante la lectura, serializando cualquier intento concurrente de reserva sobre ese mismo tenant hasta el `commit()` de la Unidad de Trabajo (`MssqlUnitOfWork`), garantizando cero saldo negativo sin interbloqueos (*deadlocks*).

### 2.3. Propagación de Contexto Asíncrono con `contextvars` y AnyIO

1. **Abstracción `TenantContext`:**
   - Implementado en `src/application/shared/tenancy/tenant_context.py` usando `contextvars.ContextVar[TenantId | None]`.
   - Python `contextvars` es nativamente compatible con el árbol de tareas de AnyIO (`anyio.create_task_group()`), propagando el contexto hacia tareas concurrentes hijas y aislándolo entre peticiones concurrentes del servidor web o del worker.
2. **Puntos de Ingesta:**
   - **HTTP (FastAPI):** `TenantContextMiddleware` inspecciona la cabecera obligatoria `X-Tenant-ID` (y/o tokens JWT). Configura el `TenantContext` al inicio del ciclo de vida del request y garantiza su limpieza en el bloque `finally:`.
   - **AMQP Worker:** El worker extrae el `tenant_id` contenido en el encabezado o payload del `EventEnvelope` y establece el `TenantContext` durante el procesamiento del mensaje.

### 2.4. Motor de Enrutamiento Dinámico de Modelos (*Dynamic Model Router*) y Fallback Resiliente

1. **Value Objects y Entidades de Dominio:**
   - `TenantId`: Slug/alfanumérico validado (3..64 caracteres).
   - `MonetaryBudget`: Saldo inmutable, moneda (`USD`), operaciones de verificación y deducción segura.
   - `ModelRoute`: Mapeo de proveedor (`openai`, `anthropic`, `gemini`), `model_id`, coste por 1.000 tokens y puntero de contingencia `fallback_model_id`.
   - `Tenant`: Aggregate Root con `TenantPolicy` (nivel de servicio: `FREE`, `STANDARD`, `ENTERPRISE`, límites por petición y lista de modelos autorizados).
2. **Servicio de Aplicación `ModelRouterService`:**
   - Recibe la política del tenant y los requisitos de la conversación (longitud de contexto, latencia objetivo, prioridad).
   - Selecciona la ruta óptima (`ModelRoute`).
   - En caso de fallo transitorio del proveedor primario (HTTP 503, 429, timeout), el worker AMQP o el servicio activa el `fallback_model_id` dentro de un bloque `anyio.create_task_group()`, emitiendo un `ModelRouteFallbackActivatedDomainEvent` para auditoría y observabilidad.

### 2.5. Modelado ORM y Migración de Esquema en MSSQL

1. **Modelos Físicos SQLModel (`src/infrastructure/persistence/mssql/models.py`):**
   - `TenantModel`: Tabla `tenants` con clave primaria `id` (VARCHAR 64), `name`, `status`, `balance_usd`, `currency`, `created_at`, `updated_at`.
   - `TenantPolicyModel`: Tabla `tenant_policies` con clave foránea `tenant_id`, `tier`, `max_tokens_per_request`, `monthly_budget_usd`, `allowed_models_json`.
   - Modificación de `ConversationModel`, `AuditLogModel` y `StreamBufferChunkModel`: Incorporan columna indexada `tenant_id: str = Field(index=True, max_length=64, nullable=False)`.
2. **Mapeador de Dominio (`TenantMapper`):**
   - Transforma bidireccionalmente la entidad `Tenant` hacia `TenantModel` y `TenantPolicyModel` respetando la pureza del dominio.
3. **Migración Alembic:**
   - `src/infrastructure/persistence/mssql/migrations/versions/0003_multi_tenant_and_budgets.py`
   - `down_revision = "0002_enterprise_auditing_and_idempotency"`.
   - Aplica scripts DDL con soporte para valores por defecto en datos preexistentes (`default_tenant`) para preservar retrocompatibilidad.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Seguridad Multi-Tenant Estricta:** Imposibilita la lectura accidental o fuga de datos entre inquilinos mediante índices discriminadores y validación defensiva en repositorios.
- **Gobernanza Financiera Sin Riesgo de Sobregiro:** Los bloqueos `ROWLOCK, UPDLOCK` impiden condiciones de carrera en alta concurrencia, rechazando peticiones que excedan la cuota con `HTTP 402 Payment Required`.
- **Alta Disponibilidad y Resiliencia en Inferencia:** Conmutación automática a modelos de contingencia (*fallback*) cuando un proveedor externo sufre degradación o interrupciones.
- **Compatibilidad con Concurrencia Estructurada:** AnyIO y `contextvars` mantienen la trazabilidad y la propagación de contexto de tenant en todo el ciclo asíncrono.
- **Adherencia Total a Clean Architecture y TDD:** El dominio permanece 100% puro en Python sin dependencias de frameworks; la persistencia y el transporte se aíslan en puertos y adaptadores probados con el ciclo `RED` -> `GREEN` -> `DOCS`.

### Negativas / Compensaciones

- **Latencia de Bloqueo en Cuentas Compartidas:** Múltiples peticiones simultáneas del *mismo* tenant que compiten por el mismo saldo se serializan brevemente durante la adquisición del lock de fila. Se mitiga manteniendo las transacciones de reserva ultra-cortas (microsegundos).
- **Sobrecarga de Migración:** Agregar `tenant_id` a tablas existentes requiere asignar un tenant por defecto a datos históricos para no romper integridad referencial.
