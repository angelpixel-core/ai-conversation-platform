"""Unit tests verifying contracts of Tool driven ports."""

import pytest
from src.domain.tools.entities.tool_approval_request import ToolApprovalRequest
from src.domain.tools.ports.sandboxed_tool_runner_port import SandboxedToolRunnerPort
from src.domain.tools.ports.tool_approval_repository_port import ToolApprovalRepositoryPort
from src.domain.tools.ports.tool_registry_port import ToolRegistryPort
from src.domain.tools.value_objects.tool_call import ToolCall
from src.domain.tools.value_objects.tool_definition import ToolDefinition
from src.domain.tools.value_objects.tool_result import ToolResult

from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeToolApprovalRepository(ToolApprovalRepositoryPort):
    def __init__(self) -> None:
        self.approvals: dict[tuple[str, str], ToolApprovalRequest] = {}

    def save(self, approval: ToolApprovalRequest) -> None:
        self.approvals[(str(approval.tenant_id), approval.id)] = approval

    def get(self, tenant_id: TenantId, approval_id: str) -> ToolApprovalRequest | None:
        return self.approvals.get((str(tenant_id), approval_id))

    def get_pending(self, tenant_id: TenantId) -> list[ToolApprovalRequest]:
        return [
            a
            for a in self.approvals.values()
            if a.tenant_id == tenant_id and a.status.value == "PENDING"
        ]


class FakeSandboxedRunner(SandboxedToolRunnerPort):
    async def execute(self, tool_call: ToolCall, timeout_seconds: float = 10.0) -> ToolResult:
        return ToolResult(
            call_id=tool_call.call_id,
            output=f"executed {tool_call.tool_name}",
            is_error=False,
            execution_time_ms=12.5,
        )


class FakeToolRegistry(ToolRegistryPort):
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._tenant_permissions: dict[str, set[str]] = {}

    def register_tool(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def allow_tool_for_tenant(self, tenant_id: TenantId, tool_name: str) -> None:
        tid_str = str(tenant_id)
        if tid_str not in self._tenant_permissions:
            self._tenant_permissions[tid_str] = set()
        self._tenant_permissions[tid_str].add(tool_name)

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, tenant_id: TenantId | None = None) -> list[ToolDefinition]:
        if tenant_id is None:
            return list(self._tools.values())
        allowed = self._tenant_permissions.get(str(tenant_id), set())
        return [t for name, t in self._tools.items() if name in allowed]

    def is_tool_allowed(self, tenant_id: TenantId, tool_name: str) -> bool:
        allowed = self._tenant_permissions.get(str(tenant_id), set())
        return tool_name in allowed and tool_name in self._tools


def test_tool_approval_repository_contract() -> None:
    repo: ToolApprovalRepositoryPort = FakeToolApprovalRepository()
    tid = TenantId("corp-acme")
    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 50})
    appr = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )

    repo.save(appr)
    fetched = repo.get(tid, "appr-1")
    assert fetched is not None
    assert fetched.tool_call.tool_name == "refund_order"

    pending = repo.get_pending(tid)
    assert len(pending) == 1
    assert pending[0].id == "appr-1"


@pytest.mark.anyio
async def test_sandboxed_runner_contract() -> None:
    runner: SandboxedToolRunnerPort = FakeSandboxedRunner()
    call = ToolCall(call_id="c-1", tool_name="echo", arguments={"text": "hello"})
    result = await runner.execute(call)

    assert result.call_id == "c-1"
    assert result.is_error is False
    assert "echo" in result.output


def test_tool_registry_contract() -> None:
    registry = FakeToolRegistry()
    t1 = ToolDefinition(
        name="weather",
        description="Get weather",
        parameters_schema={"type": "object"},
    )
    t2 = ToolDefinition(
        name="refund",
        description="Refund order",
        parameters_schema={"type": "object"},
        requires_approval=True,
    )
    registry.register_tool(t1)
    registry.register_tool(t2)

    assert registry.get_tool("weather") == t1
    assert registry.get_tool("unknown") is None

    tid = TenantId("corp-acme")
    registry.allow_tool_for_tenant(tid, "weather")

    assert registry.is_tool_allowed(tid, "weather") is True
    assert registry.is_tool_allowed(tid, "refund") is False

    allowed_tools = registry.list_tools(tenant_id=tid)
    assert len(allowed_tools) == 1
    assert allowed_tools[0].name == "weather"
