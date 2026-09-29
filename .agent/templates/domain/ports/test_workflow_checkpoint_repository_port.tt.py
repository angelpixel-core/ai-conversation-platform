"""Canonical test template: WorkflowCheckpointRepositoryPort Driven Port."""

import pytest

from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.ports.workflow_checkpoint_repository_port import WorkflowCheckpointRepositoryPort
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeWorkflowCheckpointRepository(WorkflowCheckpointRepositoryPort):
    def __init__(self) -> None:
        self.checkpoints: list[StateSnapshot] = []
        self.instances: dict[str, WorkflowInstance] = {}

    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        self.checkpoints.append(snapshot)

    def get_latest_checkpoint(self, tenant_id: TenantId, workflow_id: str) -> StateSnapshot | None:
        matching = [c for c in self.checkpoints if c.tenant_id == tenant_id and c.workflow_id == workflow_id]
        return sorted(matching, key=lambda c: c.version, reverse=True)[0] if matching else None

    def list_checkpoints(self, tenant_id: TenantId, workflow_id: str) -> list[StateSnapshot]:
        return sorted(
            [c for c in self.checkpoints if c.tenant_id == tenant_id and c.workflow_id == workflow_id],
            key=lambda c: c.version,
        )

    def save_instance(self, instance: WorkflowInstance) -> None:
        self.instances[f"{instance.tenant_id.value}:{instance.id}"] = instance

    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        return self.instances.get(f"{tenant_id.value}:{workflow_id}")


def test_fake_workflow_checkpoint_repository() -> None:
    repo = FakeWorkflowCheckpointRepository()
    tenant = TenantId("tenant-x")
    instance = WorkflowInstance("wf-1", tenant, "Test", "node-1")
    repo.save_instance(instance)

    retrieved = repo.get_instance(tenant, "wf-1")
    assert retrieved is not None
    assert retrieved.name == "Test"
