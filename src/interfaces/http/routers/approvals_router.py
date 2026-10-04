from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.tools.commands.approve_tool_execution import (
    ApproveToolExecutionCommand,
    ApproveToolExecutionCommandHandler,
)
from src.application.tools.commands.reject_tool_execution import (
    RejectToolExecutionCommand,
    RejectToolExecutionCommandHandler,
)
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import ApprovalStatus, ToolApprovalRequest
from src.domain.tools.value_objects.tool_call import ToolCall
from src.interfaces.http.tools_schemas import (
    CreateToolApprovalRequest,
    PendingApprovalResponse,
    ToolApprovalDecisionRequest,
)


def create_approvals_router(
    unit_of_work: UnitOfWorkPort,
    event_publisher: EventPublisherPort | None = None,
) -> APIRouter:
    """Factory creating APIRouter for Human-in-the-Loop tool approvals."""
    router = APIRouter(tags=["Approvals"])

    @router.post(
        "/tenants/{tenant_id}/approvals",
        response_model=PendingApprovalResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a tool execution approval request",
        description=(
            "Submits a tool call requiring Human-in-the-Loop review under tenant governance."
        ),
    )
    def create_tool_approval(
        tenant_id: str,
        request: CreateToolApprovalRequest,
    ) -> PendingApprovalResponse:
        tid = TenantId(tenant_id)
        approval_id = f"appr-{uuid4().hex[:8]}"
        call_id = request.call_id or f"call-{uuid4().hex[:8]}"
        tool_call = ToolCall(
            call_id=call_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
        )
        approval = ToolApprovalRequest.create(
            approval_id=approval_id,
            tenant_id=tid,
            conversation_id=request.conversation_id,
            tool_call=tool_call,
        )
        with unit_of_work as uow:
            uow.tool_approvals.save(approval)
            uow.commit()

        return PendingApprovalResponse(
            approval_id=approval.id,
            tenant_id=str(approval.tenant_id),
            conversation_id=approval.conversation_id,
            tool_name=approval.tool_call.tool_name,
            arguments=approval.tool_call.arguments,
            status=approval.status.value,
            created_at=approval.created_at,
            resolved_at=approval.resolved_at,
            resolved_by=approval.operator_id,
            rejection_reason=None,
        )

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

        if decision not in ("approve", "approved", "reject", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision '{request.decision}'. Must be 'approve' or 'reject'.",
            )

        with unit_of_work as uow:
            existing = uow.tool_approvals.get(tid, approval_id)
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Approval request '{approval_id}' not found for tenant '{tenant_id}'.",
                )

            if decision in ("approve", "approved"):
                handler = ApproveToolExecutionCommandHandler(
                    tool_approval_repo=uow.tool_approvals,
                    event_publisher=event_publisher,
                )
                cmd = ApproveToolExecutionCommand(
                    approval_id=approval_id,
                    tenant_id=tenant_id,
                    operator_id=request.resolved_by,
                    justification=request.reason,
                )
                try:
                    handler.handle(cmd)
                    uow.commit()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc
            else:
                reject_handler = RejectToolExecutionCommandHandler(
                    tool_approval_repo=uow.tool_approvals,
                    event_publisher=event_publisher,
                )
                reject_cmd = RejectToolExecutionCommand(
                    approval_id=approval_id,
                    tenant_id=tenant_id,
                    operator_id=request.resolved_by,
                    reason=request.reason or "Rejected by operator",
                )
                try:
                    reject_handler.handle(reject_cmd)
                    uow.commit()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc

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
