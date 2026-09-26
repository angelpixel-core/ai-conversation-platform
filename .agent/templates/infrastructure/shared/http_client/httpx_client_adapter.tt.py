"""
Template canónico para Adaptador HTTP con HTTPX (HttpxClientAdapter).
Reglas:
- Implementa HttpClientPort usando el cliente asíncrono de httpx.
- Maneja timeouts, errores de conexión y parsing JSON.
"""

from typing import Any, Mapping, Optional
import httpx

from src.application.shared.ports.http_client import HttpClientPort


class HttpxClientAdapter(HttpClientPort):
    """Adaptador de infraestructura para peticiones HTTP asíncronas con httpx."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    async def post(
        self,
        url: str,
        json_body: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=json_body, headers=headers)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
