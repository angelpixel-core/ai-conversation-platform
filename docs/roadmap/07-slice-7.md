# Roadmap de Implementación — Slice 7: Semantic Vector Search, Hybrid RAG & Knowledge Grounding

Este documento detalla la ruta de desarrollo, ingesta de conocimiento documental, búsqueda híbrida (Full-Text/Léxica + Embeddings Vectoriales) y fundamentación de respuestas (*Knowledge Grounding / Citations*) para el séptimo slice vertical de **ai-conversation-platform**, operando sobre **Microsoft SQL Server (MSSQL) 2022**, **AnyIO**, **RabbitMQ** y **FastAPI**.

---

## 🎯 Objetivo del Slice 7

Permitir que las conversaciones activas utilicen conocimiento privado y documental específico por inquilino (*Retrieval-Augmented Generation / RAG*):

1. **Pipeline de Ingesta Asíncrona de Documentos:** Carga de documentos, particionado (*chunking* con solapamiento) y generación de embeddings en segundo plano a través de workers en RabbitMQ bajo concurrencia estructurada con AnyIO.
2. **Búsqueda Híbrida en MSSQL:** Combinar búsqueda léxica (coincidencia de palabras clave) con búsqueda semántica por similitud de cosenos sobre vectores normalizados ($L_2$) almacenados en JSON (`NVARCHAR(MAX)`), compatible con MSSQL 2022 y SQLite in-memory para testing ultra-rápido (ver [ADR 0006](file:///.agent/architecture/decisions/0006-hybrid-rag-and-mssql-vector-search.md)).
3. **Knowledge Grounding & Citations:** Inyectar los fragmentos recuperados más relevantes en el contexto del prompt antes de invocar al LLM y enriquecer el stream Server-Sent Events (SSE) con eventos tipados `citation` (documento fuente, ID de chunk, número de página y score de similitud).
4. **Aislamiento Multi-Tenant Estricto:** Toda persistencia, indexación y consulta exige obligatoriamente `tenant_id: TenantId` con índices compuestos `(tenant_id, id)` y `(tenant_id, document_id)`, garantizando cero fuga de información confidencial entre inquilinos.

---

## 🏗️ Desglose Arquitectónico del Flujo

```text
[ Cliente HTTP ]
       │  (1. POST /tenants/{tenant_id}/documents -> Registra documento)
       ▼
[ FastAPI (knowledge_router.py) ]
       │  (2. Crea Document Aggregate en estado PENDING vía UnitOfWork)
       ▼
[ MSSQL DB (knowledge_documents + outbox table) ]
       │  (3. Almacena DocumentModel y registra DocumentUploadedDomainEvent en Outbox)
       ▼
[ OutboxRelay -> RabbitMQ ('ai_platform.knowledge_events' / 'knowledge.indexing.queue') ]
       │  (4. Consume evento de documento subido)
       ▼
[ AnyIO Document Indexer Worker (anyio_document_indexer_worker.py) ]
       │  (5. Divide texto en chunks con solapamiento)
       │  (6. Genera embeddings normalizados vía EmbeddingClientPort en batches)
       │  (7. Persiste DocumentChunkModel en MSSQL y marca Document como INDEXED)
       ▼
[ MSSQL DB (knowledge_document_chunks table: Content + JSON Vector Embedding) ]
       │
       │  (8. Usuario envía mensaje: SendMessageCommand)
       ▼
[ SendMessageHandler + HybridRetrieverService ]
       │  (9. Genera embedding de la query del usuario)
       │  (10. Búsqueda Híbrida: Score = α · S_vector + (1 - α) · S_lexical)
       ▼
[ Retrieved Citations (Top-K con re-ranking y umbral de relevancia) ]
       │  (11. Inyecta contexto documental en el prompt del LLM)
       ▼
[ LLM Stream Worker ]
       │  (12. Emite tokens y eventos SSE 'event: citation')
       ▼
[ Cliente HTTP (Visualiza respuesta fundamentada con badges de citas) ]
```

---

## 📐 Estrategia de Vectores y Compatibilidad MSSQL 2022 (ADR 0006)

Debido a que el entorno de despliegue utiliza Microsoft SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`) y la suite de pruebas unitarias/aplicación corre sobre SQLite in-memory (`sqlite:///:memory:`):

1. **Almacenamiento:** Los vectores flotantes se almacenan normalizados a norma $L_2 = 1.0$ y serializados en JSON (`embedding_json: str` mapeado a `NVARCHAR(MAX)` en SQL Server y `Text` en SQLite).
2. **Cálculo de Similitud:** Con norma euclidiana $||v|| = 1.0$, la similitud de cosenos equivale al producto escalar (Dot Product):
   $$\text{cosine\_similarity}(A, B) = \sum_{i=1}^{D} A_i \cdot B_i$$
3. **Búsqueda Híbrida Ponderada:**
   $$\text{Score}_{\text{híbrido}} = \alpha \cdot S_{\text{vector}} + (1 - \alpha) \cdot S_{\text{lexical}} \quad (\alpha = 0.7)$$
4. **Portabilidad y Rendimiento:** Cero dependencias binarias propietarias, 100% testeable en memoria y ejecución de tests locales en menos de 2 segundos.

---

## 🗂️ Plantillas Canónicas del Slice 7 (`.agent/templates/`)

| Artefacto / Rol | Ruta del Template Canónico | Ruta del Template de Test |
| :--- | :--- | :--- |
| **Value Object: Vector** | [.agent/templates/domain/value_objects/embedding_vector.tt.py](file:///.agent/templates/domain/value_objects/embedding_vector.tt.py) | [.agent/templates/domain/value_objects/test_embedding_vector.tt.py](file:///.agent/templates/domain/value_objects/test_embedding_vector.tt.py) |
| **Value Object: Citation** | [.agent/templates/domain/value_objects/citation.tt.py](file:///.agent/templates/domain/value_objects/citation.tt.py) | [.agent/templates/domain/value_objects/test_citation.tt.py](file:///.agent/templates/domain/value_objects/test_citation.tt.py) |
| **Aggregate: Document** | [.agent/templates/domain/entities/document_entity.tt.py](file:///.agent/templates/domain/entities/document_entity.tt.py) | [.agent/templates/domain/entities/test_document_entity.tt.py](file:///.agent/templates/domain/entities/test_document_entity.tt.py) |
| **Entity: DocumentChunk** | [.agent/templates/domain/entities/document_chunk_entity.tt.py](file:///.agent/templates/domain/entities/document_chunk_entity.tt.py) | [.agent/templates/domain/entities/test_document_chunk_entity.tt.py](file:///.agent/templates/domain/entities/test_document_chunk_entity.tt.py) |
| **Domain Events** | [.agent/templates/domain/events/knowledge_events.tt.py](file:///.agent/templates/domain/events/knowledge_events.tt.py) | [.agent/templates/domain/events/test_knowledge_events.tt.py](file:///.agent/templates/domain/events/test_knowledge_events.tt.py) |
| **Port: Knowledge Repo** | [.agent/templates/domain/ports/knowledge_repository_port.tt.py](file:///.agent/templates/domain/ports/knowledge_repository_port.tt.py) | [.agent/templates/domain/ports/test_knowledge_repository_port.tt.py](file:///.agent/templates/domain/ports/test_knowledge_repository_port.tt.py) |
| **Port: Embedding Client** | [.agent/templates/domain/ports/embedding_client_port.tt.py](file:///.agent/templates/domain/ports/embedding_client_port.tt.py) | [.agent/templates/domain/ports/test_embedding_client_port.tt.py](file:///.agent/templates/domain/ports/test_embedding_client_port.tt.py) |
| **Service: Hybrid Retriever** | [.agent/templates/application/services/hybrid_retriever_service.tt.py](file:///.agent/templates/application/services/hybrid_retriever_service.tt.py) | [.agent/templates/application/services/test_hybrid_retriever_service.tt.py](file:///.agent/templates/application/services/test_hybrid_retriever_service.tt.py) |

---

## 📋 Lista de Tareas y Checkboxes

### Fase 1: Dominio y Contratos de Conocimiento Documental (RAG)

*Entidades de documentos, value objects de chunks, embeddings, citas y eventos de dominio.*

* [x] **Value Objects de Embeddings y Citas**
  * Archivo: `src/domain/knowledge/value_objects/embedding_vector.py` (lista inmutable de flotantes tipada, normalización $L_2$, dot product cosine similarity).
  * Archivo: `src/domain/knowledge/value_objects/citation.py` (referencia inmutable de citación: source_document_id, document_name, chunk_id, page_number, similarity_score, snippet).
* [ ] **Entidades de Dominio: Document & DocumentChunk**
  * Archivo: `src/domain/knowledge/entities/document.py` (AggregateRoot administrando ciclo `PENDING` -> `PROCESSING` -> `INDEXED` / `FAILED`, validaciones y conteo de fragmentos).
  * Archivo: `src/domain/knowledge/entities/document_chunk.py` (fragmento secuencial de texto con su `EmbeddingVector` y metadata).
* [ ] **Eventos de Dominio de Ingesta y Recuperación**
  * Archivo: `src/domain/knowledge/events/knowledge_events.py`
  * Eventos: `DocumentUploadedDomainEvent`, `DocumentIndexedDomainEvent`, `DocumentIndexingFailedDomainEvent`, `KnowledgeContextRetrievedDomainEvent`.
* [ ] **Puertos de Persistencia y Modelos de Embedding (Driven Ports)**
  * Archivo: `src/domain/knowledge/ports/knowledge_repository_port.py` (`save_document`, `get_document`, `save_chunks`, `get_chunks_by_document`, `search_hybrid`).
  * Archivo: `src/domain/knowledge/ports/embedding_client_port.py` (`generate_embeddings(texts: Sequence[str]) -> list[EmbeddingVector]`).
* [ ] **Tests Unitarios de Dominio**
  * Archivo: `tests/unit/domain/knowledge/test_embedding_vector.py`
  * Archivo: `tests/unit/domain/knowledge/test_citation.py`
  * Archivo: `tests/unit/domain/knowledge/test_document.py`
  * Archivo: `tests/unit/domain/knowledge/test_document_chunk.py`
  * Archivo: `tests/unit/domain/knowledge/test_knowledge_events.py`
  * Archivo: `tests/unit/domain/knowledge/test_knowledge_ports.py`

---

### Fase 2: Capa de Aplicación (RAG Pipelines & Services)

*Orquestación de ingesta, cálculo de similitud híbrida y fundamentación del contexto en conversaciones.*

* [ ] **Comando y Handler de Carga Documental**
  * Archivo: `src/application/knowledge/commands/upload_document.py` (`UploadDocumentCommand`, `UploadDocumentResult`, `UploadDocumentHandler`).
* [ ] **Comando y Handler de Indexación de Chunks**
  * Archivo: `src/application/knowledge/commands/index_document_chunks.py` (`IndexDocumentChunksCommand`, `IndexDocumentChunksResult`, `IndexDocumentChunksHandler`).
* [ ] **Servicio de Recuperación Híbrida (HybridRetrieverService)**
  * Archivo: `src/application/knowledge/services/hybrid_retriever_service.py` (orquesta generación de embedding de consulta, búsqueda híbrida en repositorio y mapeo a `Citation`).
* [ ] **Integración en SendMessageHandler**
  * Actualización de `src/application/conversations/commands/send_message.py` para consultar `HybridRetrieverService` cuando existan bases de conocimiento y adjuntar las citas recuperadas.
* [ ] **Tests Unitarios de Aplicación**
  * Archivo: `tests/unit/application/knowledge/test_upload_document.py`
  * Archivo: `tests/unit/application/knowledge/test_index_document_chunks.py`
  * Archivo: `tests/unit/application/knowledge/test_hybrid_retriever_service.py`

---

### Fase 3: Infraestructura MSSQL (Hybrid & Vector Storage)

*Modelos relacionales consolidados, repositorio MSSQL portable y migraciones Alembic.*

* [ ] **Modelos ORM Físicos en `src/infrastructure/persistence/mssql/models.py`**
  * `DocumentModel` (tabla `knowledge_documents`): `id`, `tenant_id` (indexado), `filename`, `content_type`, `status`, `total_chunks`, `created_at`, `updated_at`.
  * `DocumentChunkModel` (tabla `knowledge_document_chunks`): `id`, `tenant_id` (indexado), `document_id` (FK a `knowledge_documents.id`), `sequence_number`, `content`, `embedding_json` (`NVARCHAR(MAX)`), `page_number`, `created_at`.
  * Índices compuestos: `(tenant_id, id)` y `(tenant_id, document_id)`.
* [ ] **Mapper de Dominio/Persistencia**
  * Archivo: `src/infrastructure/persistence/mssql/knowledge_mapper.py` (`to_domain_document`, `to_model_document`, `to_domain_chunk`, `to_model_chunk`).
* [ ] **Adaptador de Repositorio de Conocimiento en MSSQL**
  * Archivo: `src/infrastructure/persistence/mssql/mssql_knowledge_repository.py`
  * Implementa `KnowledgeRepositoryPort` con filtrado mandatorio por `tenant_id` y cálculo de score híbrido (vector dot product + token lexical overlap).
* [ ] **Adaptadores de Cliente de Embeddings**
  * Fake para tests: `src/infrastructure/embeddings/fake_embedding_client.py`.
  * Cliente HTTP real: `src/infrastructure/embeddings/httpx_embedding_client.py` (asíncrono con HTTPX y AnyIO).
* [ ] **Migración de Base de Datos Alembic**
  * Archivo: `src/infrastructure/persistence/mssql/migrations/versions/0004_knowledge_documents_and_vectors.py`
  * `down_revision = "0003_multi_tenant_and_budgets"`.
* [ ] **Tests de Integración de Persistencia**
  * Archivo: `tests/integration/infrastructure/mssql/test_mssql_knowledge_repository.py`

---

### Fase 4: RabbitMQ Ingestion Pipeline con AnyIO

*Consumo desacoplado de documentos e indexación por lotes sin degradar la API principal.*

* [ ] **Configuración de Topología RabbitMQ**
  * Archivo: `src/infrastructure/messaging/rabbitmq/knowledge_topology_config.py`
  * Exchange: `ai_platform.knowledge_events` (Topic).
  * Queue: `knowledge.indexing.queue`.
  * Routing key: `knowledge.document.uploaded`.
* [ ] **Worker Asíncrono de Indexación con AnyIO**
  * Archivo: `src/infrastructure/messaging/rabbitmq/anyio_document_indexer_worker.py`
  * Procesamiento en batches con `anyio.create_task_group()`, semáforo de concurrencia (`anyio.Semaphore`) y manejo resiliente de errores transitorios.
* [ ] **Tests de Integración del Worker de Ingesta**
  * Archivo: `tests/integration/workers/test_anyio_document_indexer_worker.py`

---

### Fase 5: Interfaces HTTP & Streaming de Citaciones

*Endpoints REST para carga de documentos, consulta de estado y citas en SSE.*

* [ ] **Esquemas DTO HTTP (Pydantic v2)**
  * Archivo: `src/interfaces/http/knowledge_schemas.py` (`DocumentUploadRequest`, `DocumentUploadResponse`, `DocumentStatusResponse`, `CitationSchema`).
* [ ] **Router de Gestión de Conocimiento**
  * Archivo: `src/interfaces/http/knowledge_router.py`
  * `POST /tenants/{tenant_id}/documents` (`202 Accepted`).
  * `GET /tenants/{tenant_id}/documents/{document_id}/status` (`200 OK`).
  * `GET /tenants/{tenant_id}/documents` (`200 OK`, listado paginado).
* [ ] **Eventos SSE de Citaciones en Streaming**
  * Actualización de `src/interfaces/http/messages_router.py` para emitir eventos estructurados:

    ```text
    event: citation
    data: {"source_document_id": "doc-1", "document_name": "manual.pdf", "chunk_id": "chk-1", "page_number": 4, "similarity_score": 0.89, "snippet": "..."}
    ```

* [ ] **Tests de Integración HTTP / E2E**
  * Archivo: `tests/integration/api/test_knowledge_router.py`
  * Archivo: `tests/integration/api/test_rag_streaming_citations.py`

---

### Fase 6: Ensamble, Inyección de Dependencias y Arquitectura Viva

* [ ] **Registro en Contenedores de Dependencias**
  * `src/container.py` y `src/worker_container.py` registrando `KnowledgeRepositoryPort`, `EmbeddingClientPort`, `HybridRetrieverService` y handlers.
* [ ] **Documento de Decisión Arquitectónica (ADR)**
  * Archivo: [.agent/architecture/decisions/0006-hybrid-rag-and-mssql-vector-search.md](file:///.agent/architecture/decisions/0006-hybrid-rag-and-mssql-vector-search.md) (completado y aceptado).
* [ ] **Actualización del Diagrama Vivo del Sistema**
  * Archivo: [.agent/architecture/system-map.mermaid.md](file:///.agent/architecture/system-map.mermaid.md) incorporando los subgrafos de Knowledge, RAG Retriever, Worker de Ingesta y tablas de chunks vectoriales.

---

## 🔍 Criterios de Aceptación del Slice 7

1. **Búsqueda Híbrida Precisa y Equilibrada:** La combinación de similitud de cosenos ($S_{\text{vector}}$) y coincidencia léxica ($S_{\text{lexical}}$) clasifica en primer lugar fragmentos relevantes tanto para consultas conceptuales como para códigos específicos o palabras clave exactas.
2. **Aislamiento Multi-Tenant Inviolable:** Todas las operaciones de inserción, lectura y búsqueda vectorial validan y filtran estrictamente por `tenant_id`. No existe vía alguna para acceder o consultar documentos de otro inquilino.
3. **Streaming con Citaciones Tipadas:** El stream SSE emite eventos `citation` estructurados y parseables que permiten al frontend renderizar fuentes documentales verificables con número de página y fragmento citado.
4. **Testing Portable Ultra-Rápido:** Toda la suite de tests unitarios e integración en memoria ejecuta en menos de 2 segundos sin dependencias de servicios externos gracias al diseño $L_2$ + JSON.
