from collections.abc import Sequence
from decimal import Decimal
from typing import Self

import pytest

from src.application.knowledge.commands.upload_document import (
    UploadDocumentCommand,
    UploadDocumentHandler,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.knowledge.entities.document import Document
from src.domain.knowledge.entities.document_chunk import DocumentChunk
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.knowledge.value_objects.embedding_vector import EmbeddingVector
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeTenantRepo(TenantRepositoryPort):
    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}

    def get(self, tenant_id: TenantId) -> Tenant | None:
        return self.tenants.get(str(tenant_id))

    def get_for_update(self, tenant_id: TenantId) -> Tenant | None:
        return self.get(tenant_id)

    def add(self, tenant: Tenant) -> None:
        self.tenants[str(tenant.id)] = tenant

    def list(self) -> list[Tenant]:
        return list(self.tenants.values())


class FakeKnowledgeRepo(KnowledgeRepositoryPort):
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], Document] = {}

    def save_document(self, document: Document) -> None:
        self.documents[(str(document.tenant_id), str(document.id))] = document

    def get_document(self, tenant_id: TenantId, document_id: str) -> Document | None:
        return self.documents.get((str(tenant_id), document_id))

    def save_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        pass

    def get_chunks_by_document(self, tenant_id: TenantId, document_id: str) -> list[DocumentChunk]:
        return []

    def search_hybrid(
        self,
        tenant_id: TenantId,
        query_text: str,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        min_score: float = 0.5,
        alpha: float = 0.7,
    ) -> list[tuple[DocumentChunk, float]]:
        return []


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.tenants = FakeTenantRepo()
        self.knowledge = FakeKnowledgeRepo()  # type: ignore[attr-defined]
        self.committed = False
        self.conversations = None  # type: ignore[assignment]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_upload_document_success() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-acme")
    uow.tenants.add(
        Tenant(tenant_id=tid, name="Acme", budget=MonetaryBudget(balance=Decimal("100.00")))
    )

    handler = UploadDocumentHandler(unit_of_work=uow)
    command = UploadDocumentCommand(
        tenant_id="corp-acme",
        filename="company_policy.pdf",
        content_type="application/pdf",
        document_id="doc-123",
    )

    result = handler.handle(command)

    assert result.document_id == "doc-123"
    assert result.tenant_id == "corp-acme"
    assert result.filename == "company_policy.pdf"
    assert result.status == "PENDING"
    assert uow.committed is True
    assert uow.knowledge.get_document(tid, "doc-123") is not None


def test_upload_document_tenant_not_found_raises_error() -> None:
    uow = FakeUnitOfWork()
    handler = UploadDocumentHandler(unit_of_work=uow)
    command = UploadDocumentCommand(
        tenant_id="missing-tenant",
        filename="manual.pdf",
    )

    with pytest.raises(ValueError, match="no encontrado"):
        handler.handle(command)


def test_upload_document_empty_filename_raises_error() -> None:
    uow = FakeUnitOfWork()
    tid = TenantId("corp-acme")
    uow.tenants.add(
        Tenant(tenant_id=tid, name="Acme", budget=MonetaryBudget(balance=Decimal("100.00")))
    )
    handler = UploadDocumentHandler(unit_of_work=uow)

    with pytest.raises(ValueError, match="vacío"):
        handler.handle(UploadDocumentCommand(tenant_id="corp-acme", filename="   "))
