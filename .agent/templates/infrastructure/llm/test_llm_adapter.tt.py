"""Template canónico para Pruebas de Integración del Adaptador LLM (Streaming Client).

Reglas:
- Verifica la generación token a token del generador asíncrono para Fake y HTTPX.
- Usa @pytest.mark.anyio para compatibilidad con el entorno de pruebas asíncronas.
"""

import httpx
import pytest

from .llm_adapter import FakeLlmClientAdapter, HttpxLlmClientAdapter


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_httpx_llm_adapter_streams_sse_tokens() -> None:
    # Arrange: simular stream SSE estilo OpenAI
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Hola"}}]}\n\n'
        'data: {"choices": [{"delta": {"content": " mundo"}}]}\n\n'
        'data: [DONE]\n\n'
    )

    def sse_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "text/event-stream"},
            content=sse_body.encode("utf-8"),
        )

    transport = httpx.MockTransport(sse_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    adapter = HttpxLlmClientAdapter(
        api_key="sk-fake-test-key",
        base_url="https://api.fake-openai.com/v1",
        client=mock_client,
    )

    # Act
    tokens = [t async for t in adapter.stream_chat(messages=[{"role": "user", "content": "Hi"}])]

    # Assert
    assert tokens == ["Hola", " mundo"]
