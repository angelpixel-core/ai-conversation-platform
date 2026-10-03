"""Integration tests for stream fallback when assistant message is already persisted or buffered."""

import pytest
from fastapi.testclient import TestClient

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import SendMessageHandler
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.persistence.in_memory.in_memory_stream_buffer_repository import (
    InMemoryStreamBufferRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


@pytest.mark.anyio
async def test_stream_endpoint_falls_back_to_buffered_chunks_when_assistant_already_replied() -> (
    None
):
    uow = InMemoryUnitOfWork()
    buffer_repo = InMemoryStreamBufferRepositoryAdapter()
    recovery_service = StreamRecoveryService(buffer_repo=buffer_repo)

    conversation = Conversation.create("Test Conversation")
    conversation.append_user_message("Initial prompt")
    conversation.append_assistant_message("Respuesta simulada del asistente IA.")
    with uow:
        uow.conversations.add(conversation)
        uow.commit()

    conv_id_str = str(conversation.id)
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(1, "Respuesta ", is_final=False))
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(2, "simulada ", is_final=False))
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(3, "del ", is_final=False))
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(4, "asistente ", is_final=False))
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(5, "IA.", is_final=False))
    await buffer_repo.append_chunk(conv_id_str, StreamChunk.create(6, "", is_final=True))

    llm = FakeLlmClientAdapter()
    stream_handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm,
    )

    app = build_api(
        create_conversation_handler=CreateConversationHandler(unit_of_work=uow),
        send_message_handler=SendMessageHandler(unit_of_work=uow),
        stream_conversation_handler=stream_handler,
        stream_recovery_service=recovery_service,
        unit_of_work=uow,
    )
    client = TestClient(app)

    # Act
    resp = client.get(f"/conversations/{conversation.id}/stream")

    # Assert
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "data: Respuesta " in body
    assert "data: simulada " in body
    assert "data: del " in body
    assert "data: asistente " in body
    assert "data: IA." in body
    assert "data: [DONE]" in body


@pytest.mark.anyio
async def test_stream_endpoint_falls_back_to_persisted_assistant_message_if_no_buffer() -> None:
    uow = InMemoryUnitOfWork()

    conversation = Conversation.create("Test Conversation Without Buffer")
    conversation.append_user_message("What is AI?")
    conversation.append_assistant_message("Artificial Intelligence is smart.")
    with uow:
        uow.conversations.add(conversation)
        uow.commit()

    llm = FakeLlmClientAdapter()
    stream_handler = StreamConversationQueryHandler(
        conversation_repository=uow.conversations,
        llm_client=llm,
    )

    app = build_api(
        create_conversation_handler=CreateConversationHandler(unit_of_work=uow),
        send_message_handler=SendMessageHandler(unit_of_work=uow),
        stream_conversation_handler=stream_handler,
        unit_of_work=uow,
    )
    client = TestClient(app)

    # Act
    resp = client.get(f"/conversations/{conversation.id}/stream")

    # Assert
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "data: Artificial " in body
    assert "data: Intelligence " in body
    assert "data: is " in body
    assert "data: smart." in body
    assert "data: [DONE]" in body
