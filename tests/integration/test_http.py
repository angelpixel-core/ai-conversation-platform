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


def test_send_message_endpoint__when_conversation_exists__returns_200_with_message() -> None:
    client = TestClient(create_app())

    # Create conversation first
    create_resp = client.post("/conversations", json={"title": "Test Chat"})
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # Send message
    msg_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Hello AI assistant!"},
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["conversation_id"] == conv_id
    assert data["role"] == "user"
    assert data["content"] == "Hello AI assistant!"
    assert "created_at" in data


def test_send_message_endpoint__when_conversation_not_found__returns_404() -> None:
    client = TestClient(create_app())

    from uuid import uuid4

    random_id = uuid4()
    msg_resp = client.post(
        f"/conversations/{random_id}/messages",
        json={"content": "Hello"},
    )
    assert msg_resp.status_code == 404


def test_send_message_endpoint__when_empty_content__returns_422() -> None:
    client = TestClient(create_app())

    from uuid import uuid4

    random_id = uuid4()
    msg_resp = client.post(
        f"/conversations/{random_id}/messages",
        json={"content": ""},
    )
    assert msg_resp.status_code == 422


def test_stream_conversation_endpoint__when_valid_conversation__returns_sse_stream() -> None:
    client = TestClient(create_app())

    # Create conversation and add a user message
    create_resp = client.post("/conversations", json={"title": "Streaming Chat"})
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    msg_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Tell me a story"},
    )
    assert msg_resp.status_code == 200

    # Stream conversation tokens via SSE
    stream_resp = client.get(f"/conversations/{conv_id}/stream")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")
    assert "data:" in stream_resp.text
    assert "[DONE]" in stream_resp.text


def test_stream_conversation_endpoint__when_conversation_not_found__returns_404() -> None:
    client = TestClient(create_app())

    from uuid import uuid4

    random_id = uuid4()
    stream_resp = client.get(f"/conversations/{random_id}/stream")
    assert stream_resp.status_code == 404


def test_stream_conversation_endpoint__when_no_messages__returns_400() -> None:
    client = TestClient(create_app())

    create_resp = client.post("/conversations", json={"title": "Empty Chat"})
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    stream_resp = client.get(f"/conversations/{conv_id}/stream")
    assert stream_resp.status_code == 400


def test_stream_conversation_endpoint__when_invalid_temperature__returns_400() -> None:
    client = TestClient(create_app())

    from uuid import uuid4

    random_id = uuid4()
    stream_resp = client.get(f"/conversations/{random_id}/stream?temperature=5.0")
    assert stream_resp.status_code == 400


def test_endpoints__when_handlers_not_configured__return_500() -> None:
    from uuid import uuid4

    from src.interfaces.http.api import build_api

    app = build_api()
    client = TestClient(app)
    random_id = uuid4()

    resp_create = client.post("/conversations", json={"title": "Test"})
    assert resp_create.status_code == 500

    resp_msg = client.post(f"/conversations/{random_id}/messages", json={"content": "Hi"})
    assert resp_msg.status_code == 500

    resp_stream = client.get(f"/conversations/{random_id}/stream")
    assert resp_stream.status_code == 500

