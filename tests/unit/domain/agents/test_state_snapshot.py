"""Unit tests for StateSnapshot Value Object."""

from datetime import UTC, datetime

import pytest

from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_state_snapshot_valid_creation() -> None:
    now = datetime.now(UTC)
    snapshot = StateSnapshot(
        checkpoint_id="chk-001",
        tenant_id=TenantId("corp-acme"),
        workflow_id="wf-12345",
        current_node="supervisor",
        state_data={"task": "contract_analysis", "findings": ["clause_1", "clause_2"]},
        version=1,
        status="RUNNING",
        created_at=now,
    )
    assert snapshot.checkpoint_id == "chk-001"
    assert snapshot.tenant_id.value == "corp-acme"
    assert snapshot.workflow_id == "wf-12345"
    assert snapshot.current_node == "supervisor"
    assert snapshot.version == 1
    assert snapshot.status == "RUNNING"
    assert snapshot.state_data["task"] == "contract_analysis"
    assert snapshot.created_at == now


def test_state_snapshot_empty_checkpoint_id_raises_error() -> None:
    with pytest.raises(ValueError, match="checkpoint_id"):
        StateSnapshot(
            checkpoint_id="   ",
            tenant_id=TenantId("corp-acme"),
            workflow_id="wf-123",
            current_node="supervisor",
            state_data={},
            version=1,
        )


def test_state_snapshot_empty_workflow_id_raises_error() -> None:
    with pytest.raises(ValueError, match="workflow_id"):
        StateSnapshot(
            checkpoint_id="chk-001",
            tenant_id=TenantId("corp-acme"),
            workflow_id="",
            current_node="supervisor",
            state_data={},
            version=1,
        )


def test_state_snapshot_empty_current_node_raises_error() -> None:
    with pytest.raises(ValueError, match="current_node"):
        StateSnapshot(
            checkpoint_id="chk-001",
            tenant_id=TenantId("corp-acme"),
            workflow_id="wf-123",
            current_node="  ",
            state_data={},
            version=1,
        )


def test_state_snapshot_invalid_version_raises_error() -> None:
    with pytest.raises(ValueError, match="versión"):
        StateSnapshot(
            checkpoint_id="chk-001",
            tenant_id=TenantId("corp-acme"),
            workflow_id="wf-123",
            current_node="supervisor",
            state_data={},
            version=0,
        )


def test_state_snapshot_invalid_state_data_type_raises_error() -> None:
    with pytest.raises(ValueError, match="diccionario"):
        StateSnapshot(
            checkpoint_id="chk-001",
            tenant_id=TenantId("corp-acme"),
            workflow_id="wf-123",
            current_node="supervisor",
            state_data="not-a-dict",  # type: ignore[arg-type]
            version=1,
        )
