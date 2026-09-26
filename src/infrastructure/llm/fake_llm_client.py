"""Fake LLM client adapter for deterministic testing without external API calls."""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence

from src.application.shared.ports.llm_client import LlmClientPort


class FakeLlmClientAdapter(LlmClientPort):
    """Fake adapter simulating AI model streaming response with controlled latency."""

    def __init__(self, canned_response: str = "Respuesta simulada del asistente IA.") -> None:
        self._canned_response = canned_response

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        """Stream simulated canned response token by token."""
        words = self._canned_response.split(" ")
        for word in words:
            await asyncio.sleep(0.005)  # Simulate network / token latency
            yield f"{word} "
