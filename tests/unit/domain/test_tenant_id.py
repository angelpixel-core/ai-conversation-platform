"""Unit tests for TenantId value object."""

import pytest
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_tenant_id_valid_creation() -> None:
    tid = TenantId("acme-corp")
    assert tid.value == "acme-corp"
    assert str(tid) == "acme-corp"


def test_tenant_id_normalizes_to_lower_and_strips() -> None:
    tid = TenantId("  AcMe-CoRp  ")
    assert tid.value == "acme-corp"


def test_tenant_id_immutability() -> None:
    tid = TenantId("acme-corp")
    with pytest.raises(AttributeError):
        tid.value = "another-tenant"  # type: ignore[misc]


def test_tenant_id_empty_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede estar vacío"):
        TenantId("   ")


def test_tenant_id_too_short_raises_error() -> None:
    with pytest.raises(ValueError, match="entre 3 y 64 caracteres"):
        TenantId("ab")


def test_tenant_id_too_long_raises_error() -> None:
    with pytest.raises(ValueError, match="entre 3 y 64 caracteres"):
        TenantId("a" * 65)


def test_tenant_id_invalid_characters_raises_error() -> None:
    with pytest.raises(ValueError, match="caracteres inválidos"):
        TenantId("acme_corp_invalid$")


def test_tenant_id_equality_and_hash() -> None:
    tid1 = TenantId("acme-corp")
    tid2 = TenantId("acme-corp")
    tid3 = TenantId("other-corp")

    assert tid1 == tid2
    assert tid1 != tid3
    assert hash(tid1) == hash(tid2)
