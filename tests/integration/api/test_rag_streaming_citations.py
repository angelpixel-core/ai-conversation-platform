"""Integration tests for RAG streaming with citation SSE events (Phase 5 RED)."""

from collections.abc import AsyncIterator, Mapping, Sequence

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.embeddings.fake_embedding_client import (
    FakeEmbeddingClientAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter
from src.interfaces.http.api import build_api


class StubLlmClient(LlmClientPort):
    """Stub LLM client producing tokens."""

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        for token in ["Based ", "on ", "policy, ", "Clean ", "Architecture ", "applies."]:
            yield token


@pytest.mark.anyio
async def test_sse_streaming_emits_citation_events() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    tenant_id = TenantId("acme-corp")

    # 1. Seed document and chunk with embedding
    vector = EmbeddingVector.from_list([1.0, 0.0, 0.0, 0.0])
    with uow:
        doc = Document.create("doc-1", tenant_id, "architecture_handbook.pdf")
        doc.mark_processing()
        doc.mark_indexed(total_chunks=1)
        uow.knowledge.save_document(doc)

        chunk = DocumentChunk(
            chunk_id="chk-1",
            document_id="doc-1",
            tenant_id=tenant_id,
            sequence_number=0,
            content="Clean Architecture principles mandate layer separation.",
            embedding=vector,
            page_number=12,
        )
        uow.knowledge.save_chunks([chunk])

        # 2. Seed conversation with user query matching chunk
        conv = Conversation.create(title="Architecture discussion")
        conv.append_user_message("What does Clean Architecture mandate?")
        uow.conversations.add(conv)
        uow.commit()
        conv_id = conv.id

    embedding_client = FakeEmbeddingClientAdapter(dimension=4)
    retriever_service = HybridRetrieverService(
        embedding_client=embedding_client,
        knowledge_repository=uow.knowledge,
    )
    llm_client = StubLlmClient()
    stream_handler = StreamConversationQueryHandler(
        unit_of_work=uow,
        llm_client=llm_client,
    )

    app = build_api(
        unit_of_work=uow,
        stream_conversation_handler=stream_handler,
        retriever_service=retriever_service,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/conversations/{conv_id}/stream",
            headers={"X-Tenant-Id": str(tenant_id)},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        body_text = response.text
        # Assert citation event was emitted before data tokens
        assert "event: citation" in body_text
        assert "architecture_handbook.pdf" in body_text
        assert "doc-1" in body_text
        assert "chk-1" in body_text
        # Assert data tokens were emitted
        assert "data: Based " in body_text
        assert "data: [DONE]" in body_text
