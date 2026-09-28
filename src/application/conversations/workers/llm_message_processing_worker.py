"""LLM Message Processing Worker handler for background inference."""

import logging
from typing import Any
from uuid import UUID

from src.application.conversations.commands.append_assistant_message import (
    AppendAssistantMessageCommand,
    AppendAssistantMessageHandler,
)
from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.stream_chunk import StreamChunk
from src.domain.shared.events.event_envelope import EventEnvelope

logger = logging.getLogger(__name__)


class LlmMessageProcessingWorker:
    """Asynchronous worker consumer that orchestrates LLM chat completion for user messages."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        llm_client: LlmClientPort,
        append_handler: AppendAssistantMessageHandler | None = None,
        stream_buffer_repo: StreamBufferRepositoryPort | None = None,
        audit_repo: AuditRepositoryPort | None = None,
        idempotency_repo: IdempotencyRepositoryPort | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._llm_client = llm_client
        self._append_handler = append_handler or AppendAssistantMessageHandler(
            unit_of_work=unit_of_work
        )
        self._stream_buffer_repo = stream_buffer_repo
        self._audit_repo = audit_repo
        self._idempotency_repo = idempotency_repo

    def _should_skip_event(self, envelope: EventEnvelope) -> bool:
        payload: dict[str, Any] = envelope.payload
        message_data = payload.get("message")
        role = message_data.get("role") if isinstance(message_data, dict) else payload.get("role")
        if role != "user":
            logger.debug("Skipping non-user message event %s with role=%s", envelope.id, role)
            return True
        return False

    def _extract_conversation_id(self, payload: dict[str, Any], envelope_id: Any) -> UUID:
        conversation_id_raw = payload.get("conversation_id")
        if not conversation_id_raw:
            raise ValueError(f"Missing 'conversation_id' in event payload for event {envelope_id}.")
        return (
            conversation_id_raw
            if isinstance(conversation_id_raw, UUID)
            else UUID(str(conversation_id_raw))
        )

    async def _try_acquire_idempotency(self, key: str, envelope_id: Any) -> bool:
        if self._idempotency_repo is None:
            return True
        acquired = await self._idempotency_repo.try_acquire(key, ttl_seconds=300)
        if not acquired:
            existing = await self._idempotency_repo.get(key)
            if existing is not None and existing.status in (
                IdempotencyStatus.COMPLETED,
                IdempotencyStatus.PENDING,
            ):
                logger.info(
                    "Event %s already processed or in-flight (status=%s). Skipping duplicate.",
                    envelope_id,
                    existing.status,
                )
                return False
        return True

    async def _stream_and_buffer_tokens(
        self, stream_id: str, messages: list[dict[str, str]]
    ) -> tuple[list[str], str]:
        tokens: list[str] = []
        seq = 1
        async for token in self._llm_client.stream_chat(messages=messages):
            tokens.append(token)
            if self._stream_buffer_repo is not None:
                chunk = StreamChunk.create(
                    sequence_number=seq,
                    content=token,
                    is_final=False,
                )
                await self._stream_buffer_repo.append_chunk(stream_id=stream_id, chunk=chunk)
            seq += 1

        if self._stream_buffer_repo is not None:
            final_chunk = StreamChunk.create(sequence_number=seq, content="", is_final=True)
            await self._stream_buffer_repo.append_chunk(stream_id=stream_id, chunk=final_chunk)

        return tokens, "".join(tokens)

    async def _record_audit_log(
        self,
        conversation_id: UUID,
        stream_id: str,
        tokens: list[str],
        response: str,
        envelope_id: Any,
    ) -> None:
        if self._audit_repo is None:
            return
        audit_record = AuditLogRecord.create(
            event_name="llm_inference_completed",
            actor_id="worker:llm_message_processing_worker",
            resource_type="conversation",
            resource_id=str(conversation_id),
            action="chat_completion",
            payload={
                "stream_id": stream_id,
                "total_chunks": len(tokens),
                "character_count": len(response),
                "event_id": str(envelope_id),
            },
            tokens_consumed=len(tokens),
        )
        await self._audit_repo.record(audit_record)

    async def handle(self, envelope: EventEnvelope) -> None:
        """Process an incoming event envelope containing an appended message."""
        if self._should_skip_event(envelope):
            return

        payload: dict[str, Any] = envelope.payload
        conversation_id = self._extract_conversation_id(payload, envelope.id)
        idempotency_key = f"worker:event:{envelope.id}"

        if not await self._try_acquire_idempotency(idempotency_key, envelope.id):
            return

        try:
            with self._unit_of_work as uow:
                conversation = uow.conversations.get(conversation_id)
                if conversation is None:
                    raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
                messages = [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in conversation.messages
                ]

            stream_id = str(payload.get("stream_id") or conversation_id)
            tokens, response = await self._stream_and_buffer_tokens(stream_id, messages)

            command = AppendAssistantMessageCommand(
                conversation_id=conversation_id, content=response
            )
            self._append_handler.handle(command)

            await self._record_audit_log(conversation_id, stream_id, tokens, response, envelope.id)

            if self._idempotency_repo is not None:
                await self._idempotency_repo.mark_completed(
                    key=idempotency_key,
                    response_code=200,
                    response_body={"conversation_id": str(conversation_id)},
                )

            logger.info("Successfully appended assistant response for conv %s.", conversation_id)

        except Exception as exc:
            if self._idempotency_repo is not None:
                await self._idempotency_repo.mark_failed(
                    key=idempotency_key, error_message=str(exc)
                )
            raise

    async def __call__(self, envelope: EventEnvelope) -> None:
        """Allow direct callable invocation satisfying EventHandler protocol."""
        await self.handle(envelope)
