"""
Template canónico para Pruebas de Integración del Adaptador LLM (Streaming Client).
Reglas:
- Verifica la generación token a token del generador asíncrono.
"""

import pytest

from .llm_adapter import FakeLlmClientAdapter


@pytest.mark.asyncio
async def test_fake_llm_adapter_streams_tokens() -> None:
    # Arrange
    adapter = FakeLlmClientAdapter(canned_response="Hola mundo desde IA.")

    # Act
    tokens = []
    async for token in adapter.stream_chat(messages=[{"role": "user", "content": "Hola"}]):
        tokens.append(token)

    # Assert
    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert "Hola mundo desde IA." in full_text
