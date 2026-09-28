"""Unit tests for TenantContext asynchronous and synchronous propagation."""

import anyio
import pytest
from src.application.shared.tenancy.tenant_context import (
    async_tenant_context,
    get_current_tenant_id,
    tenant_context,
)


def test_tenant_context_default_is_none() -> None:
    assert get_current_tenant_id() is None


def test_tenant_context_sync_manager() -> None:
    assert get_current_tenant_id() is None
    with tenant_context("tenant-corp-1"):
        assert get_current_tenant_id() == "tenant-corp-1"
    assert get_current_tenant_id() is None


@pytest.mark.anyio
async def test_tenant_context_async_manager() -> None:
    assert get_current_tenant_id() is None
    async with async_tenant_context("tenant-corp-2"):
        assert get_current_tenant_id() == "tenant-corp-2"
    assert get_current_tenant_id() is None


def test_tenant_context_nested_scopes() -> None:
    assert get_current_tenant_id() is None
    with tenant_context("outer-tenant"):
        assert get_current_tenant_id() == "outer-tenant"
        with tenant_context("inner-tenant"):
            assert get_current_tenant_id() == "inner-tenant"
        assert get_current_tenant_id() == "outer-tenant"
    assert get_current_tenant_id() is None


@pytest.mark.anyio
async def test_tenant_context_isolated_in_anyio_task_group() -> None:
    results: dict[str, str | None] = {}

    async def worker(tenant_name: str) -> None:
        async with async_tenant_context(tenant_name):
            await anyio.sleep(0.01)
            results[tenant_name] = get_current_tenant_id()

    async with anyio.create_task_group() as tg:
        tg.start_soon(worker, "tenant-a")
        tg.start_soon(worker, "tenant-b")

    assert results["tenant-a"] == "tenant-a"
    assert results["tenant-b"] == "tenant-b"
    assert get_current_tenant_id() is None
