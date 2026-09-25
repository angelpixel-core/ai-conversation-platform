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


def test_openapi_docs_endpoints() -> None:
    client = TestClient(create_app())

    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    assert openapi_resp.json()["info"]["title"] == "AI Conversation Platform API"
