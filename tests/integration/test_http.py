from fastapi.testclient import TestClient

from src.main import create_app


def test_create_conversation_endpoint() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/conversations",
        json={"title": "AI demo"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "AI demo"
    assert "id" in body
