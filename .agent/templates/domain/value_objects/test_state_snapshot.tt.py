"""Canonical test template: StateSnapshot Value Object."""

import pytest

from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_state_snapshot_valid() -> None:
    snapshot = StateSnapshot(
        checkpoint_id="chk-001",
        tenant_id=TenantId("tenant-acme"),
        workflow_id="wf-999",
        current_node="supervisor",
        state_data={"task": "audit contract", "findings": []},
        version=1,
        status="RUNNING",
    )
    assert snapshot.checkpoint_id == "chk-001"
    assert snapshot.tenant_id.value == "tenant-acme"
    assert snapshot.version == 1
    assert snapshot.state_data["task"] == "audit contract"


def test_state_snapshot_invalid_version() -> None:
    with pytest.raises(ValueError, match="versión"):
        StateSnapshot(
            checkpoint_id="chk-001",
            tenant_id=TenantId("tenant-acme"),
            workflow_id="wf-999",
            current_node="supervisor",
            state_data={},
            version=0,
        )
