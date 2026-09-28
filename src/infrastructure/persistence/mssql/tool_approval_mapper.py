"""Mapper between ToolApprovalRequest domain entity and ToolApprovalModel."""

import json

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.value_objects.tool_call import ToolCall
from src.infrastructure.persistence.mssql.models import ToolApprovalModel


class ToolApprovalMapper:
    """Translates between ToolApprovalRequest aggregate and ToolApprovalModel ORM."""

    @staticmethod
    def to_model(entity: ToolApprovalRequest) -> ToolApprovalModel:
        return ToolApprovalModel(
            id=entity.id,
            tenant_id=str(entity.tenant_id),
            conversation_id=entity.conversation_id,
            call_id=entity.tool_call.call_id,
            tool_name=entity.tool_call.tool_name,
            arguments_json=json.dumps(entity.tool_call.arguments),
            status=entity.status.value,
            operator_id=entity.operator_id,
            justification=entity.justification,
            created_at=entity.created_at,
            resolved_at=entity.resolved_at,
        )

    @staticmethod
    def to_entity(model: ToolApprovalModel) -> ToolApprovalRequest:
        arguments = json.loads(model.arguments_json)
        tool_call = ToolCall(
            call_id=model.call_id,
            tool_name=model.tool_name,
            arguments=arguments,
            created_at=model.created_at,
        )
        return ToolApprovalRequest(
            approval_id=model.id,
            tenant_id=TenantId(model.tenant_id),
            conversation_id=model.conversation_id,
            tool_call=tool_call,
            status=ApprovalStatus(model.status),
            operator_id=model.operator_id,
            justification=model.justification,
            created_at=model.created_at,
            resolved_at=model.resolved_at,
        )
