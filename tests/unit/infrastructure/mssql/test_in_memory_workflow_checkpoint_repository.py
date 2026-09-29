"""Unit tests for InMemoryWorkflowCheckpointRepository adapter."""

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.in_memory_workflow_checkpoint_repository import (
    InMemoryWorkflowCheckpointRepositoryAdapter,
)


def test_in_memory_workflow_checkpoint_repo_roundtrip() -> None:
    repo = InMemoryWorkflowCheckpointRepositoryAdapter()
    tenant_id = TenantId("corp-acme")
    other_tenant = TenantId("corp-other")

    instance = WorkflowInstance.create(
        workflow_id="wf-mem-1",
        tenant_id=tenant_id,
        name="Memory Test",
        initial_node="supervisor",
    )
    repo.save_instance(instance)

    assert repo.get_instance(tenant_id, "wf-mem-1") is not None
    assert repo.get_instance(other_tenant, "wf-mem-1") is None

    snap = instance.transition_to("researcher", {"test": True})
    repo.save_checkpoint(snap)

    latest = repo.get_latest_checkpoint(tenant_id, "wf-mem-1")
    assert latest is not None
    assert latest.version == 2
    assert latest.current_node == "researcher"

    assert repo.get_latest_checkpoint(other_tenant, "wf-mem-1") is None
