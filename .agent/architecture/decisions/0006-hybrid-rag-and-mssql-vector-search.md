# ADR 0006: Búsqueda Híbrida Semántica (RAG), Almacenamiento Vectorial en MSSQL y Citaciones Multi-Tenant

- **Estado:** Aceptado (Accepted)
- **Fecha:** 2026-09-28
- **Autores:** Core Architecture Team
- **Contexto del Slice:** Slice 7 — Semantic Vector Search, Hybrid RAG & Knowledge Grounding

---

## 1. Contexto y Problemática

Al integrar capacidades de Generación Aumentada por Recuperación (*Retrieval-Augmented Generation / RAG*) en la plataforma conversacional, surgen requerimientos técnicos y arquitectónicos clave:

1. **Alucinaciones y Falta de Fundamentación (*Knowledge Grounding*):**
   - Los modelos de lenguaje base carecen de acceso a información privada, manuales corporativos y políticas internas. Se requiere inyectar contexto documental relevante y verificable en los prompts, acompañando las respuestas con citas exactas (documento fuente, fragmento, página/score) en el stream SSE.
2. **Aislamiento Multi-Tenant Estricto en Conocimiento:**
   - La plataforma es multi-inquilino (Slice 6). Los documentos confidenciales del *Tenant A* jamás deben ser indexados ni recuperados en búsquedas del *Tenant B*. El filtrado por `tenant_id` debe ser mandatorio e ineludible en el repositorio y la base de datos.
3. **Almacenamiento Vectorial en Microsoft SQL Server 2022 y Portabilidad de Tests:**
   - La base de datos relacional de producción es Microsoft SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`). Aunque las extensiones vectoriales nativas (`VECTOR_DISTANCE`) se encuentran en preview en Azure SQL / SQL Server 2025, el motor de SQL Server 2022 en Linux y las pruebas unitarias locales en SQLite in-memory requieren una estrategia de almacenamiento de vectores flotantes portable, eficiente y libre de dependencias propietarias o binarias externas.
4. **Búsqueda Híbrida (Léxica + Semántica):**
   - La búsqueda puramente vectorial falla ante términos exactos (códigos de producto, identificadores, números de error o acrónimos). La búsqueda puramente léxica falla ante sinonimias y consultas conceptuales. Es imperativo un motor de búsqueda híbrida que combine coincidencias léxicas con similitud semántica.
5. **Ingesta Asíncrona sin Bloquear la API:**
   - La extracción de texto, particionado (*chunking*) y generación de embeddings mediante APIs externas son operaciones lentas (cientos de milisegundos o segundos). No pueden realizarse en el ciclo de vida síncrono del request HTTP.

---

## 2. Decisión de Diseño

Se adopta una solución integral basada en Clean Architecture, DDD, CQRS, AnyIO y almacenamiento relacional en MSSQL:

### 2.1. Modelo de Dominio de Conocimiento (DDD)

1. **Value Objects:**
   - `EmbeddingVector`: Tupla inmutable de números flotantes de dimensión fija (1536 por defecto para OpenAI `text-embedding-3-*` o configurable a 768 / 384). Incluye normalización $L_2$ ($||v|| = 1.0$) y cálculo de similitud de cosenos por producto escalar.
   - `Citation`: Representa la referencia verificable a una fuente documental (`source_document_id`, `document_name`, `chunk_id`, `page_number`, `similarity_score`, `snippet`).
   - `DocumentId` y `ChunkId`: Identificadores únicos inmutables.
2. **Entidades:**
   - `Document` (`AggregateRoot`): Agregado que administra el ciclo de vida de un documento (`PENDING` -> `PROCESSING` -> `INDEXED` / `FAILED`), metadata, inquilino propietario (`tenant_id: TenantId`), nombre de archivo y número de chunks. Emite `DocumentUploadedDomainEvent` e `DocumentIndexedDomainEvent`.
   - `DocumentChunk` (`Entity`): Fragmento de texto extraído con su índice secuencial (`sequence_number`), contenido textual, vector de embedding (`EmbeddingVector`) y metadata de paginación.

### 2.2. Estrategia de Almacenamiento de Vectores en SQL Server 2022 y SQLite

1. **Esquema Relacional en SQLModel (`src/infrastructure/persistence/mssql/models.py`):**
   - `DocumentModel` (tabla `knowledge_documents`): `id`, `tenant_id` (indexado), `filename`, `content_type`, `status`, `total_chunks`, `created_at`, `updated_at`.
   - `DocumentChunkModel` (tabla `knowledge_document_chunks`): `id`, `tenant_id` (indexado), `document_id` (FK), `sequence_number`, `content`, `embedding_json` (`NVARCHAR(MAX)` / `Text`), `page_number`.
   - Índices compuestos: `(tenant_id, id)` y `(tenant_id, document_id)`.
2. **Serialización y Similitud Vectorial:**
   - Los vectores se almacenan serializados en formato JSON (`embedding_json: str`) en la base de datos relacional.
   - Al estar los vectores normalizados a norma $L_2 = 1.0$:
     $$\text{cosine\_similarity}(A, B) = \sum_{i=1}^{D} A_i \cdot B_i \quad (\text{Dot Product})$$
     $$\text{cosine\_distance}(A, B) = 1.0 - \text{cosine\_similarity}(A, B)$$
   - Esta formulación matemática garantiza compatibilidad total tanto en Microsoft SQL Server como en SQLite in-memory para testing automatizado ultra-rápido (<1s).

### 2.3. Motor de Búsqueda Híbrida y Fusión de Re-ranking

1. **Filtrado Defensivo de Inquilino:**
   - Toda consulta SQL o in-memory exige obligatoriamente `tenant_id`. Ningún fragmento de otro tenant es consultado.
2. **Fusión Ponderada de Re-ranking:**
   - La búsqueda híbrida evalúa candidatos filtrados combinando:
     - **Puntuación Semántica ($S_{\text{vector}}$):** Similitud de cosenos entre el vector de la consulta y el vector del fragmento ($[0.0, 1.0]$).
     - **Puntuación Léxica ($S_{\text{lexical}}$):** Coincidencia de términos clave / token overlap normalizado ($[0.0, 1.0]$).
     - **Score Final:**
       $$\text{Score}_{\text{híbrido}} = \alpha \cdot S_{\text{vector}} + (1 - \alpha) \cdot S_{\text{lexical}} \quad (\alpha = 0.7)$$
   - Retorna los Top-$K$ fragmentos con score superior al umbral mínimo de relevancia (`min_score = 0.65`).

### 2.4. Ingesta Asíncrona con RabbitMQ y AnyIO

1. **Ingesta HTTP:**
   - `POST /tenants/{tenant_id}/documents` valida el inquilino activo (`X-Tenant-ID`), crea la entidad `Document` en estado `PENDING` y registra un `DocumentUploadedDomainEvent` en la tabla Transactional Outbox dentro de la misma Unidad de Trabajo.
   - Responde inmediatamente con `HTTP 202 Accepted` y el `document_id`.
2. **Worker de Indexación:**
   - El `OutboxRelay` publica el evento en el topic exchange de RabbitMQ (`ai_platform.knowledge_events`).
   - El worker asíncrono (`anyio_document_indexer_worker.py`) consume el mensaje bajo concurrencia estructurada con `anyio.create_task_group()` y control de concurrencia (`anyio.Semaphore`).
   - Fragmenta el texto con overlap (ej. chunks de 500 caracteres con 50 de solapamiento), invoca a `EmbeddingClientPort` en lotes, persiste los `DocumentChunk` y actualiza el documento a `INDEXED`.

### 2.5. Fundamentación en Conversaciones y Streaming de Citaciones (SSE)

1. **Inyección de Contexto en Prompt:**
   - Cuando un usuario envía un mensaje (`SendMessageCommand`), el servicio de aplicación `HybridRetrieverService` recupera los Top-$K$ fragmentos más relevantes del tenant.
   - Los fragmentos se formatean e inyectan en el prompt del sistema antes de llamar al modelo LLM.
2. **Eventos SSE de Citaciones:**
   - En el endpoint `GET /conversations/{id}/stream`, el flujo de Server-Sent Events emite eventos estructurados de citas antes o al concluir los tokens de respuesta:

     ```text
     event: citation
     data: {"chunk_id": "chk-123", "document_name": "manual.pdf", "page_number": 4, "score": 0.89, "snippet": "..."}
     ```

   - Esto permite a la interfaz cliente renderizar insignias interactivas (*badges*) con las fuentes exactas.

---

## 3. Consecuencias y Beneficios

### Positivas

- **Aislamiento Multi-Tenant Inviolable:** Cero fuga de datos documentales entre inquilinos mediante discriminador `tenant_id` e índices compuestos.
- **Portabilidad Absoluta:** La serialización JSON y normalización $L_2$ permite ejecutar la suite de pruebas al 100% en memoria/SQLite sin requerir extensiones compiladas de C ni dependencias privativas.
- **Máxima Relevancia con Búsqueda Híbrida:** Supera las limitaciones de la búsqueda puramente semántica al ponderar palabras clave exactas y conceptos abstractos.
- **Alta Disponibilidad sin Bloqueo de API:** La ingesta masiva y vectorización se ejecutan de manera asíncrona a través de RabbitMQ y AnyIO.
- **Trazabilidad Empresarial con Citaciones:** Respuestas fundamentadas en fuentes concretas con metadatos de fragmento y página.

### Negativas / Compensaciones

- **Sobrecarga de Almacenamiento:** Los vectores de 1536 dimensiones en JSON requieren aproximadamente 8-12 KB por chunk en base de datos.
- **Llamadas a Modelos de Embedding:** Cada ingesta y consulta de usuario requiere generar vectores de embedding, consumiendo tokens de proveedor (mitigado mediante caché y batches).
