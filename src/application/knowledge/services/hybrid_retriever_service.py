"""Hybrid retriever service combining lexical search and vector similarity."""

from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.citation import Citation
from src.domain.tenants.value_objects.tenant_id import TenantId


class HybridRetrieverService:
    """Orchestrates hybrid retrieval (vector semantic + lexical) to ground conversations."""

    def __init__(
        self,
        embedding_client: EmbeddingClientPort,
        knowledge_repository: KnowledgeRepositoryPort,
    ) -> None:
        self._embedding_client = embedding_client
        self._knowledge_repository = knowledge_repository

    async def retrieve_context(
        self,
        tenant_id: TenantId,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[Citation]:
        """Retrieves top grounded citations for a tenant query using hybrid scoring."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        vectors = await self._embedding_client.generate_embeddings([cleaned_query])
        if not vectors:
            return []
        query_vector = vectors[0]

        scored_chunks = self._knowledge_repository.search_hybrid(
            tenant_id=tenant_id,
            query_text=cleaned_query,
            query_vector=query_vector,
            top_k=top_k,
            min_score=min_score,
            alpha=alpha,
        )

        citations: list[Citation] = []
        doc_cache: dict[str, str] = {}

        for chunk, score in scored_chunks:
            if chunk.document_id not in doc_cache:
                doc = self._knowledge_repository.get_document(tenant_id, chunk.document_id)
                doc_cache[chunk.document_id] = doc.filename if doc else "unknown_document"

            citations.append(
                Citation(
                    source_document_id=chunk.document_id,
                    document_name=doc_cache[chunk.document_id],
                    chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    similarity_score=min(max(float(round(score, 4)), 0.0), 1.0),
                    snippet=chunk.content[:250],
                )
            )

        return citations
