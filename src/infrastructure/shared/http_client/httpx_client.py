from typing import Any

import httpx

from src.application.shared.ports.http_client import HttpClientPort


class HttpxHttpClientAdapter(HttpClientPort):
    """HTTP adapter used for external network requests and service integrations."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.default_timeout = timeout

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        kwargs.setdefault("timeout", self.default_timeout)
        async with httpx.AsyncClient() as client:
            return await client.request(method, url, **kwargs)


__all__ = ["HttpxHttpClientAdapter"]
