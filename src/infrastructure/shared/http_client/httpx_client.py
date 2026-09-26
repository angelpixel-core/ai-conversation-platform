from typing import Any

import httpx

from src.application.shared.ports.http_client import HttpClient


class HttpxClient(HttpClient):
    """HTTP adapter used by future LLM and external-service integrations."""

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.request(method, url, **kwargs)
