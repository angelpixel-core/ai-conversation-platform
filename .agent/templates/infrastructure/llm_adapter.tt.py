"""
Template canónico para Adaptadores de Infraestructura LLM (Fake & HTTP/API).
Reglas:
- Implementan LlmClientPort.
- Adaptador Fake genera tokens deterministas con retardos de streaming controlados (asyncio.sleep).
- Adaptador Real consume endpoints HTTP de proveedores AI utilizando httpx de forma asíncrona.
"""

import asyncio
from typing import AsyncIterator, List, Mapping, Any

from src.application.shared.ports.llm_client import LlmClientPort


class FakeLlmClientAdapter(LlmClientPort):
    """Adaptador Fake para pruebas unitarias e integración sin conexión real."""

    def __init__(self, canned_response: str = "Respuesta simulada del asistente IA.") -> None:
        self._canned_response = canned_response

    async def stream_chat(
        self,
        messages: List[Mapping[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        words = self._canned_response.split(" ")
        for word in words:
            await asyncio.sleep(0.01)  # Simular latencia de red/token
            yield f"{word} "
