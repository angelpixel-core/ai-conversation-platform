"""Real LLM client adapter for OpenAI-compatible SSE endpoints using HTTPX."""

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import httpx

from src.application.shared.ports.llm_client import LlmClientPort


class HttpxLlmClientAdapter(LlmClientPort):
    """Adapter connecting to OpenAI-compatible chat completion SSE streaming APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._client = client

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from an OpenAI-compatible SSE endpoint."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        client = (
            self._client if self._client is not None else httpx.AsyncClient(timeout=self._timeout)
        )
        should_close = self._client is None

        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    clean_line = line.strip()
                    if not clean_line or clean_line.startswith(":"):
                        continue
                    if clean_line.startswith("data: "):
                        data_str = clean_line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data: dict[str, Any] = json.loads(data_str)
                            choices: list[dict[str, Any]] = data.get("choices", [])
                            if choices:
                                delta: dict[str, Any] = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield str(content)
                        except json.JSONDecodeError:
                            continue
        finally:
            if should_close:
                await client.aclose()
