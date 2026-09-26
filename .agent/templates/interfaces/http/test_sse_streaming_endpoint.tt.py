"""
Template canónico para Pruebas de Integración de Endpoints SSE Streaming (FastAPI TestClient).
Reglas:
- Verifica apertura de canal HTTP text/event-stream y recepción progresiva de eventos SSE.
"""

from uuid import uuid4
from fastapi.testclient import TestClient

from src.main import create_app


def test_sse_streaming_endpoint_returns_event_stream() -> None:
    client = TestClient(create_app())
    conversation_id = uuid4()

    # Act
    response = client.get(f"/conversations/{conversation_id}/stream")

    # Assert
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "data:" in response.text
