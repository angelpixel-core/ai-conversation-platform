"""Integration tests for Knowledge REST Router (Phase 5 RED)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter
from src.interfaces.http.api import build_api


@pytest.fixture
def uow() -> InMemoryUnitOfWorkAdapter:
    return InMemoryUnitOfWorkAdapter()


@pytest.mark.anyio
async def test_upload_document_endpoint_returns_202_accepted(
    uow: InMemoryUnitOfWorkAdapter,
) -> None:
    app = build_api(unit_of_work=uow)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tenants/acme-corp/documents",
            json={
                "filename": "security-handbook.pdf",
                "content": "Enterprise security requirements and procedures.",
                "content_type": "application/pdf",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert "document_id" in data
        assert data["tenant_id"] == "acme-corp"
        assert data["filename"] == "security-handbook.pdf"
        assert data["status"] in ("PENDING", "PROCESSING", "INDEXED")


@pytest.mark.anyio
async def test_get_document_status_endpoint(uow: InMemoryUnitOfWorkAdapter) -> None:
    app = build_api(unit_of_work=uow)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload document
        upload_resp = await client.post(
            "/tenants/acme-corp/documents",
            json={
                "filename": "guidelines.txt",
                "content": "Engineering standards and coding guidelines.",
            },
        )
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]

        # 2. Get status for correct tenant
        status_resp = await client.get(f"/tenants/acme-corp/documents/{doc_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["document_id"] == doc_id
        assert status_data["tenant_id"] == "acme-corp"
        assert status_data["filename"] == "guidelines.txt"
        assert "status" in status_data

        # 3. Cross-tenant isolation returns 404
        cross_resp = await client.get(f"/tenants/other-tenant/documents/{doc_id}/status")
        assert cross_resp.status_code == 404


@pytest.mark.anyio
async def test_get_nonexistent_document_status_returns_404(uow: InMemoryUnitOfWorkAdapter) -> None:
    app = build_api(unit_of_work=uow)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tenants/acme-corp/documents/nonexistent-doc/status")
        assert response.status_code == 404
