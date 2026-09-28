"""Relational Tool Approval repository adapter for Microsoft SQL Server."""

from sqlmodel import Session, select

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.infrastructure.persistence.mssql.models import ToolApprovalModel
from src.infrastructure.persistence.mssql.tool_approval_mapper import (
    ToolApprovalMapper,
)


class MssqlToolApprovalRepository(ToolApprovalRepositoryPort):
    """Relational persistence adapter for tool approval requests in MSSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, approval: ToolApprovalRequest) -> None:
        """Persists or updates an approval request."""
        model = ToolApprovalMapper.to_model(approval)
        self._session.merge(model)
        self._session.flush()

    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        """Retrieves an approval request by tenant and id."""
        statement = select(ToolApprovalModel).where(
            ToolApprovalModel.tenant_id == str(tenant_id),
            ToolApprovalModel.id == approval_id,
        )
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return ToolApprovalMapper.to_entity(model)

    def get_for_update(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        """Retrieves an approval request acquiring a pessimistic row lock in MSSQL."""
        statement = (
            select(ToolApprovalModel)
            .where(
                ToolApprovalModel.tenant_id == str(tenant_id),
                ToolApprovalModel.id == approval_id,
            )
            .with_for_update()
        )
        model = self._session.exec(statement).first()
        if model is None:
            return None
        return ToolApprovalMapper.to_entity(model)

    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        """Retrieves all pending approval requests for a tenant."""
        statement = select(ToolApprovalModel).where(
            ToolApprovalModel.tenant_id == str(tenant_id),
            ToolApprovalModel.status == ApprovalStatus.PENDING.value,
        )
        models = self._session.exec(statement).all()
        return [ToolApprovalMapper.to_entity(m) for m in models]
