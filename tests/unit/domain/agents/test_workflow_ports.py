"""Unit tests verifying contracts of Agent Workflow driven ports."""

import pytest

from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.ports.agent_catalog_port import AgentCatalogPort
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.agent_role import AgentRole
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


class FakeAgentCatalog(AgentCatalogPort):
    def __init__(self) -> None:
        self.roles: dict[str, AgentRole] = {}

    def register_agent(self, agent_name: str, role: AgentRole) -> None:
        self.roles[agent_name] = role

    def get_agent_role(self, agent_name: str) -> AgentRole | None:
        return self.roles.get(agent_name)

    def list_available_agents(self, tenant_id: TenantId) -> list[str]:
        return list(self.roles.keys())


def test_workflow_checkpoint_repository_port_contract() -> None:
    repo = FakeWorkflowCheckpointRepository()
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create("wf-1", tenant, "Contract Analysis", "supervisor")
    repo.save_instance(instance)

    retrieved = repo.get_instance(tenant, "wf-1")
    assert retrieved is not None
    assert retrieved.name == "Contract Analysis"

    snap1 = instance.transition_to("researcher", {"step": 1})
    repo.save_checkpoint(snap1)
    snap2 = instance.transition_to("summarizer", {"step": 2})
    repo.save_checkpoint(snap2)

    latest = repo.get_latest_checkpoint(tenant, "wf-1")
    assert latest is not None
    assert latest.version == 3
    assert latest.current_node == "summarizer"

    all_snaps = repo.list_checkpoints(tenant, "wf-1")
    assert len(all_snaps) == 2
    assert all_snaps[0].version == 2
    assert all_snaps[1].version == 3


def test_agent_catalog_port_contract() -> None:
    catalog = FakeAgentCatalog()
    tenant = TenantId("corp-acme")
    catalog.register_agent("researcher_agent", AgentRole.SPECIALIST)
    catalog.register_agent("supervisor_agent", AgentRole.SUPERVISOR)

    role = catalog.get_agent_role("researcher_agent")
    assert role == AgentRole.SPECIALIST

    agents = catalog.list_available_agents(tenant)
    assert "researcher_agent" in agents
    assert "supervisor_agent" in agents
