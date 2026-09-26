"""Integration tests for LLM client adapters (Fake and HTTPX)."""

import json
from typing import Any

import httpx
import pytest

from src.application.shared.ports.llm_client import LlmClientPort
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.llm.httpx_llm_client import HttpxLlmClientAdapter


class TestFakeLlmClientAdapter:
    """Tests for FakeLlmClientAdapter."""

    def test_implements_llm_client_port(self) -> None:
        adapter = FakeLlmClientAdapter()
        assert isinstance(adapter, LlmClientPort)

    @pytest.mark.anyio
    async def test_stream_chat__with_default_canned_response__yields_simulated_tokens(self) -> None:
        adapter = FakeLlmClientAdapter()
        messages = [{"role": "user", "content": "Hola"}]

        tokens: list[str] = []
        async for token in adapter.stream_chat(messages):
            tokens.append(token)

        assert "".join(tokens) == "Respuesta simulada del asistente IA. "
        assert len(tokens) == 5

    @pytest.mark.anyio
    async def test_stream_chat__with_custom_canned_response__yields_custom_tokens(self) -> None:
        custom_text = "Test custom stream"
        adapter = FakeLlmClientAdapter(canned_response=custom_text)
        messages = [{"role": "user", "content": "Test"}]

        tokens: list[str] = []
        async for token in adapter.stream_chat(messages):
            tokens.append(token)

        assert tokens == ["Test ", "custom ", "stream "]


class TestHttpxLlmClientAdapter:
    """Tests for HttpxLlmClientAdapter with mock HTTPX SSE streaming."""

    def test_implements_llm_client_port(self) -> None:
        adapter = HttpxLlmClientAdapter(api_key="test-key")
        assert isinstance(adapter, LlmClientPort)

    @pytest.mark.anyio
    async def test_stream_chat__with_valid_sse_stream__yields_delta_tokens(self) -> None:
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hola"}}]}\n\n',
            'data: {"choices": [{"delta": {"content": " mundo"}}]}\n\n',
            "data: [DONE]\n\n",
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer test-api-key"
            assert request.headers["Content-Type"] == "application/json"
            body = json.loads(request.read())
            assert body["model"] == "gpt-4o-mini"
            assert body["stream"] is True
            assert body["temperature"] == 0.7
            assert body["max_tokens"] == 1000
            assert body["messages"] == [{"role": "user", "content": "Hola"}]
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content="".join(sse_lines).encode("utf-8"),
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpxLlmClientAdapter(
                api_key="test-api-key",
                client=client,
            )
            tokens: list[str] = []
            async for token in adapter.stream_chat([{"role": "user", "content": "Hola"}]):
                tokens.append(token)

            assert tokens == ["Hola", " mundo"]

    @pytest.mark.anyio
    async def test_stream_chat__with_sse_keepalive_comments_and_empty_lines__filters_properly(
        self,
    ) -> None:
        sse_lines = [
            ": keepalive\n\n",
            "\n\n",
            'data: {"choices": [{"delta": {"content": "Token1"}}]}\n\n',
            ": ping\n\n",
            'data: {"choices": [{"delta": {}}]}\n\n',
            'data: {"choices": [{"delta": {"content": " Token2"}}]}\n\n',
            "data: [DONE]\n\n",
        ]

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content="".join(sse_lines).encode("utf-8"),
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpxLlmClientAdapter(api_key="key", client=client)
            tokens: list[str] = []
            async for token in adapter.stream_chat([{"role": "user", "content": "Hi"}]):
                tokens.append(token)

            assert tokens == ["Token1", " Token2"]

    @pytest.mark.anyio
    async def test_stream_chat__with_malformed_json_chunk__skips_safely(self) -> None:
        sse_lines = [
            "data: not-a-json-object\n\n",
            'data: {"choices": [{"delta": {"content": "Recovered"}}]}\n\n',
            "data: [DONE]\n\n",
        ]

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content="".join(sse_lines).encode("utf-8"),
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpxLlmClientAdapter(api_key="key", client=client)
            tokens: list[str] = []
            async for token in adapter.stream_chat([{"role": "user", "content": "Hi"}]):
                tokens.append(token)

            assert tokens == ["Recovered"]

    @pytest.mark.anyio
    async def test_stream_chat__when_http_error_occurs__raises_http_status_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "Unauthorized"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpxLlmClientAdapter(api_key="bad-key", client=client)
            with pytest.raises(httpx.HTTPStatusError):
                async for _ in adapter.stream_chat([{"role": "user", "content": "Hi"}]):
                    pass

    @pytest.mark.anyio
    async def test_stream_chat__without_injected_client__instantiates_and_closes_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        closed = False

        class CustomMockClient(httpx.AsyncClient):
            async def aclose(self) -> None:
                nonlocal closed
                closed = True
                await super().aclose()

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=b'data: {"choices": [{"delta": {"content": "ok"}}]}\n\ndata: [DONE]\n\n',
            )

        transport = httpx.MockTransport(handler)

        def mock_client_factory(**kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = transport
            return CustomMockClient(**kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", mock_client_factory)

        adapter = HttpxLlmClientAdapter(api_key="key", client=None)
        tokens: list[str] = []
        async for token in adapter.stream_chat([{"role": "user", "content": "Hi"}]):
            tokens.append(token)

        assert tokens == ["ok"]
        assert closed is True
