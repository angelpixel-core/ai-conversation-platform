"""Test template canónico para MssqlTenantRepository."""

from decimal import Decimal
from unittest.mock import MagicMock
from src.domain.tenants.entities.tenant_entity import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from .mssql_tenant_repository import MssqlTenantRepository
from .tenant_model import TenantModel


def test_mssql_tenant_repository_add() -> None:
    session_mock = MagicMock()
    repo = MssqlTenantRepository(session=session_mock)

    tenant = Tenant(
        tenant_id=TenantId("tenant-mock"),
        name="Mock Tenant",
        budget=MonetaryBudget(balance=Decimal("100.00")),
    )

    repo.add(tenant)
    assert session_mock.merge.called
    assert session_mock.flush.called


def test_mssql_tenant_repository_get_not_found() -> None:
    session_mock = MagicMock()
    exec_result_mock = MagicMock()
    exec_result_mock.first.return_value = None
    session_mock.exec.return_value = exec_result_mock

    repo = MssqlTenantRepository(session=session_mock)
    result = repo.get(TenantId("missing-id"))
    assert result is None
