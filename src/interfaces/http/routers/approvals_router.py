"""Human-in-the-Loop (HITL) Tool Approval HTTP Router."""

from fastapi import APIRouter, HTTPException, status

from src.application.shared.ports.event_publisher import EventPublisher
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.application.tools.commands.approve_tool_execution import (
    ApproveToolExecutionCommand,
    ApproveToolExecutionHandler,
)
from src.application.tools.commands.reject_tool_execution import (
    RejectToolExecutionCommand,
    RejectToolExecutionHandler,
)
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import ApprovalStatus
from src.interfaces.http.tools_schemas import (
    PendingApprovalResponse,
    ToolApprovalDecisionRequest,
)


def create_approvals_router(
    unit_of_work: UnitOfWork,
    event_publisher: EventPublisher | None = None,
) -> APIRouter:
    """Factory creating APIRouter for Human-in-the-Loop tool approvals."""
    router = APIRouter(tags=["Approvals"])

    @router.get(
        "/tenants/{tenant_id}/approvals/pending",
        response_model=list[PendingApprovalResponse],
        status_code=status.HTTP_200_OK,
        summary="List pending tool execution approvals",
        description="Retrieves all tool approvals pending review for a given tenant.",
    )
    def list_pending_approvals(tenant_id: str) -> list[PendingApprovalResponse]:
        tid = TenantId(tenant_id)
        with unit_of_work as uow:
            approvals = uow.tool_approvals.get_pending(tid)
            return [
                PendingApprovalResponse(
                    approval_id=appr.id,
                    tenant_id=str(appr.tenant_id),
                    conversation_id=appr.conversation_id,
                    tool_name=appr.tool_call.tool_name,
                    arguments=appr.tool_call.arguments,
                    status=appr.status.value,
                    created_at=appr.created_at,
                    resolved_at=appr.resolved_at,
                    resolved_by=appr.operator_id,
                    rejection_reason=(
                        appr.justification if appr.status == ApprovalStatus.REJECTED else None
                    ),
                )
                for appr in approvals
            ]

    @router.post(
        "/tenants/{tenant_id}/approvals/{approval_id}/decision",
        response_model=PendingApprovalResponse,
        status_code=status.HTTP_200_OK,
        summary="Approve or reject a pending tool execution",
        description="Records an operator approval or rejection decision on a pending tool call.",
    )
    def submit_approval_decision(
        tenant_id: str,
        approval_id: str,
        request: ToolApprovalDecisionRequest,
    ) -> PendingApprovalResponse:
        tid = TenantId(tenant_id)
        decision = request.decision.strip().lower()

        with unit_of_work as uow:
            existing = uow.tool_approvals.get(tid, approval_id)
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Approval request '{approval_id}' not found for tenant '{tenant_id}'.",
                )

        if decision in ("approve", "approved"):
            handler = ApproveToolExecutionHandler(
                tool_approval_repo=unit_of_work.tool_approvals,
                event_publisher=event_publisher,
            )
            cmd = ApproveToolExecutionCommand(
                approval_id=approval_id,
                tenant_id=tenant_id,
                operator_id=request.resolved_by,
                justification=request.reason,
            )
            with unit_of_work as uow:
                try:
                    handler.handle(cmd)
                    uow.commit()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc
        elif decision in ("reject", "rejected"):
            reject_handler = RejectToolExecutionHandler(
                tool_approval_repo=unit_of_work.tool_approvals,
                event_publisher=event_publisher,
            )
            reject_cmd = RejectToolExecutionCommand(
                approval_id=approval_id,
                tenant_id=tenant_id,
                operator_id=request.resolved_by,
                reason=request.reason or "Rejected by operator",
            )
            with unit_of_work as uow:
                try:
                    reject_handler.handle(reject_cmd)
                    uow.commit()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision '{request.decision}'. Must be 'approve' or 'reject'.",
            )

        with unit_of_work as uow:
            updated = uow.tool_approvals.get(tid, approval_id)
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Approval request '{approval_id}' not found.",
                )
            return PendingApprovalResponse(
                approval_id=updated.id,
                tenant_id=str(updated.tenant_id),
                conversation_id=updated.conversation_id,
                tool_name=updated.tool_call.tool_name,
                arguments=updated.tool_call.arguments,
                status=updated.status.value,
                created_at=updated.created_at,
                resolved_at=updated.resolved_at,
                resolved_by=updated.operator_id,
                rejection_reason=(
                    updated.justification if updated.status == ApprovalStatus.REJECTED else None
                ),
            )

    return router
