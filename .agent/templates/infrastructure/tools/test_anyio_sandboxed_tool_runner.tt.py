"""Canonical test template: AnyioSandboxedToolRunner."""

import anyio
import pytest

from src.domain.tools.value_objects.tool_call import ToolCall
from src.infrastructure.tools.anyio_sandboxed_tool_runner import AnyioSandboxedToolRunner


def sample_calc(a: int, b: int) -> int:
    return a + b


async def slow_fn() -> str:
    await anyio.sleep(2.0)
    return "done"


@pytest.mark.anyio
async def test_runner_executes_successfully() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"calc": sample_calc})
    call = ToolCall(call_id="c-1", tool_name="calc", arguments={"a": 3, "b": 7})

    result = await runner.execute(call, timeout_seconds=1.0)
    assert result.call_id == "c-1"
    assert result.is_error is False
    assert result.output == "10"


@pytest.mark.anyio
async def test_runner_aborts_on_timeout() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"slow": slow_fn})
    call = ToolCall(call_id="c-2", tool_name="slow", arguments={})

    result = await runner.execute(call, timeout_seconds=0.1)
    assert result.is_error is True
    assert "límite de tiempo" in result.output
