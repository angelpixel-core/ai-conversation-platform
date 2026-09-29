"""Unit tests for MssqlWorkflowCheckpointRepository adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import (
    ConversationModel,
    TenantModel,
)
from src.infrastructure.persistence.mssql.mssql_workflow_checkpoint_repository import (
    MssqlWorkflowCheckpointRepository,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed parent tenant
        tenant = TenantModel(id="corp-acme", name="Acme Corp")
        other_tenant = TenantModel(id="corp-other", name="Other Corp")
        session.add(tenant)
        session.add(other_tenant)
        session.commit()
        yield session


def test_mssql_workflow_checkpoint_repo_instance_lifecycle(sqlite_session: Session) -> None:
    repo = MssqlWorkflowCheckpointRepository(session=sqlite_session)
    tenant_id = TenantId("corp-acme")
    other_tenant = TenantId("corp-other")

    instance = WorkflowInstance.create(
        workflow_id="wf-500",
        tenant_id=tenant_id,
        name="Contract Review",
        initial_node="supervisor",
        initial_state={"goal": "review"},
    )
    repo.save_instance(instance)
    sqlite_session.commit()

    retrieved = repo.get_instance(tenant_id, "wf-500")
    assert retrieved is not None
    assert retrieved.id == "wf-500"
    assert retrieved.name == "Contract Review"
    assert retrieved.status == WorkflowStatus.RUNNING

    # Multi-tenant isolation
    assert repo.get_instance(other_tenant, "wf-500") is None


def test_mssql_workflow_checkpoint_repo_checkpoints(sqlite_session: Session) -> None:
    repo = MssqlWorkflowCheckpointRepository(session=sqlite_session)
    tenant_id = TenantId("corp-acme")
    other_tenant = TenantId("corp-other")

    instance = WorkflowInstance.create(
        workflow_id="wf-600",
        tenant_id=tenant_id,
        name="Parallel Pipeline",
        initial_node="supervisor",
    )
    repo.save_instance(instance)

    snap1 = instance.transition_to("researcher", {"step": 1})
    repo.save_checkpoint(snap1)
    snap2 = instance.transition_to("summarizer", {"step": 2})
    repo.save_checkpoint(snap2)
    sqlite_session.commit()

    latest = repo.get_latest_checkpoint(tenant_id, "wf-600")
    assert latest is not None
    assert latest.version == 3
    assert latest.current_node == "summarizer"

    all_snaps = repo.list_checkpoints(tenant_id, "wf-600")
    assert len(all_snaps) == 2
    assert all_snaps[0].version == 2
    assert all_snaps[1].version == 3

    # Cross-tenant isolation
    assert repo.get_latest_checkpoint(other_tenant, "wf-600") is None
    assert repo.list_checkpoints(other_tenant, "wf-600") == []
