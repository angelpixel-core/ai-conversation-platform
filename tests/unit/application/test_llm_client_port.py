"""Unit tests for LlmClientPort abstract contract."""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence

import pytest

from src.application.shared.ports.llm_client import LlmClientPort


def test_cannot_instantiate_abstract_llm_client_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LlmClientPort()  # type: ignore[abstract]


def test_concrete_llm_client_port_implementation() -> None:
    class DummyLlmClient(LlmClientPort):
        async def stream_chat(
            self,
            messages: Sequence[Mapping[str, str]],
            temperature: float = 0.7,
            max_tokens: int = 1000,
        ) -> AsyncIterator[str]:
            yield "Hello"
            yield " World"

    async def collect_tokens() -> list[str]:
        client = DummyLlmClient()
        return [token async for token in client.stream_chat([{"role": "user", "content": "Hi"}])]

    tokens = asyncio.run(collect_tokens())

    assert tokens == ["Hello", " World"]
