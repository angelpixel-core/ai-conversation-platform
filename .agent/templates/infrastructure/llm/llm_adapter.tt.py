"""Template canónico para Adaptadores de Infraestructura LLM (Fake & HTTP/API).

Reglas:
- Implementan LlmClientPort.
- Adaptador Fake genera tokens deterministas con retardos de streaming controlados (asyncio.sleep).
- Adaptador Real consume endpoints HTTP de proveedores AI utilizando httpx de forma asíncrona (SSE).
"""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
import json
from typing import Any

import httpx

from src.application.shared.ports.llm_client import LlmClientPort


class FakeLlmClientAdapter(LlmClientPort):
    """Adaptador Fake para pruebas unitarias e integración sin conexión real."""

    def __init__(self, canned_response: str = "Respuesta simulada del asistente IA.") -> None:
        self._canned_response = canned_response

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        words = self._canned_response.split(" ")
        for word in words:
            await asyncio.sleep(0.01)  # Simular latencia de red/token
            yield f"{word} "


class HttpxLlmClientAdapter(LlmClientPort):
    """Adaptador real para proveedores compatibles con OpenAI/SSE usando HTTPX."""

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
        messages: Sequence[Mapping[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
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
            self._client
            if self._client is not None
            else httpx.AsyncClient(timeout=self._timeout)
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
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        finally:
            if should_close:
                await client.aclose()
