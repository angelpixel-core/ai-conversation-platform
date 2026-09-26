"""Abstract LLM Client Port for streaming AI responses."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping, Sequence


class LlmClientPort(ABC):
    """Driven port interface for LLM completion streaming."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from an AI model.

        Args:
            messages: List of chat messages [{'role': 'user', 'content': '...'}].
            temperature: Sampling temperature for model output.
            max_tokens: Maximum tokens allowed in response.

        Yields:
            str: Each generated token delta.
        """
        yield ""  # pragma: no cover
