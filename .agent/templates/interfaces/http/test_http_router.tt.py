"""
Template canónico para Pruebas de Integración de Endpoints HTTP / Streaming (FastAPI TestClient).
Reglas:
- Verifica respuestas HTTP, códigos de estado (200, 201, 400), validaciones de esquemas Pydantic y SSE.
"""

from fastapi.testclient import TestClient

from src.main import create_app


def test_create_conversation_endpoint_returns_201() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/conversations",
        json={"title": "Demo test"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Demo test"
    assert "id" in body


def test_health_check_endpoint_returns_200() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
