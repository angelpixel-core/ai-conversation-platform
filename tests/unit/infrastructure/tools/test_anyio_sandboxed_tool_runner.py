"""Unit tests for AnyioSandboxedToolRunner."""

import anyio
import pytest

from src.domain.tools.value_objects.tool_call import ToolCall
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunner,
)


def sample_calc(a: int, b: int) -> int:
    return a + b


async def async_greet(name: str) -> str:
    return f"Hello, {name}!"


async def slow_fn() -> str:
    await anyio.sleep(2.0)
    return "done"


def faulty_tool() -> None:
    raise RuntimeError("Third party API failed")


@pytest.mark.anyio
async def test_runner_executes_sync_handler_successfully() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"calc": sample_calc})
    call = ToolCall(call_id="c-1", tool_name="calc", arguments={"a": 3, "b": 7})

    result = await runner.execute(call, timeout_seconds=1.0)
    assert result.call_id == "c-1"
    assert result.is_error is False
    assert result.output == "10"
    assert result.execution_time_ms >= 0


@pytest.mark.anyio
async def test_runner_executes_async_handler_successfully() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"greet": async_greet})
    call = ToolCall(call_id="c-2", tool_name="greet", arguments={"name": "Alice"})

    result = await runner.execute(call, timeout_seconds=1.0)
    assert result.call_id == "c-2"
    assert result.is_error is False
    assert result.output == "Hello, Alice!"


@pytest.mark.anyio
async def test_runner_aborts_on_timeout() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"slow": slow_fn})
    call = ToolCall(call_id="c-3", tool_name="slow", arguments={})

    result = await runner.execute(call, timeout_seconds=0.1)
    assert result.call_id == "c-3"
    assert result.is_error is True
    assert "límite de tiempo" in result.output


@pytest.mark.anyio
async def test_runner_handles_exception_defensively() -> None:
    runner = AnyioSandboxedToolRunner(registry_handlers={"faulty": faulty_tool})
    call = ToolCall(call_id="c-4", tool_name="faulty", arguments={})

    result = await runner.execute(call, timeout_seconds=1.0)
    assert result.call_id == "c-4"
    assert result.is_error is True
    assert "Third party API failed" in result.output


@pytest.mark.anyio
async def test_runner_returns_error_for_unregistered_tool() -> None:
    runner = AnyioSandboxedToolRunner()
    call = ToolCall(call_id="c-5", tool_name="missing_handler", arguments={})

    result = await runner.execute(call)
    assert result.call_id == "c-5"
    assert result.is_error is True
    assert "no encontrada en el sandbox" in result.output
