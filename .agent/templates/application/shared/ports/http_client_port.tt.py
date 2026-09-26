"""
Template canónico para el Puerto Secundario de Cliente HTTP (HttpClientPort).
Reglas:
- Definido en la capa de aplicación como contrato abstracto (ABC).
- Aísla las peticiones HTTP externas (httpx, requests, aiohttp).
"""

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional


class HttpClientPort(ABC):
    """Puerto abstracto para ejecuciones de peticiones HTTP externas."""

    @abstractmethod
    async def post(
        self,
        url: str,
        json_body: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
    ) -> Mapping[str, Any]:
        """Ejecuta una petición HTTP POST asíncrona."""
        pass
