"""
Template canónico para un Puerto Secundario / Driven Port de LLM (AI Streaming Client).
Reglas:
- Definido en la capa de aplicación/compartidos como contrato abstracto (ABC).
- Utiliza generadores asíncronos (AsyncIterator[str]) para streaming reactivo de tokens.
- No importa ni depende de SDKs o librerías de infraestructura de terceros (OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Mapping, Any


class LlmClientPort(ABC):
    """Puerto abstracto para proveedores de LLM con soporte de streaming token a token."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Mapping[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        """Envía un historial de mensajes al LLM y retorna un generador asíncrono de tokens.

        Args:
            messages: Historial de mensajes [{'role': 'user', 'content': '...'}].
            temperature: Creatividad del modelo.
            max_tokens: Límite máximo de tokens de salida.

        Yields:
            str: Cada delta/token generado por el modelo en tiempo real.
        """
        yield ""
