"""LLM Message Processing Worker handler for background inference."""

import logging
from typing import Any
from uuid import UUID

from src.application.conversations.commands.append_assistant_message import (
    AppendAssistantMessageCommand,
    AppendAssistantMessageHandler,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.shared.events.event_envelope import EventEnvelope

logger = logging.getLogger(__name__)


class LlmMessageProcessingWorker:
    """Asynchronous worker consumer that orchestrates LLM chat completion for user messages."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        llm_client: LlmClientPort,
        append_handler: AppendAssistantMessageHandler | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._llm_client = llm_client
        self._append_handler = append_handler or AppendAssistantMessageHandler(
            unit_of_work=unit_of_work
        )

    async def handle(self, envelope: EventEnvelope) -> None:
        """Process an incoming event envelope containing an appended message.

        Args:
            envelope: Event envelope with payload containing conversation_id and message details.

        Raises:
            ValueError: If required fields (e.g. conversation_id) are missing.
            ConversationNotFoundError: If the conversation aggregate cannot be found.
            Exception: Propagates any LLM or repository error to enable DLQ routing.
        """
        payload: dict[str, Any] = envelope.payload

        # Extract role
        message_data = payload.get("message")
        if isinstance(message_data, dict):
            role = message_data.get("role")
        else:
            role = payload.get("role")

        # Skip processing if message is not from user (e.g. prevent recursive assistant replies)
        if role != "user":
            logger.debug(
                "Skipping non-user message event %s with role=%s",
                envelope.id,
                role,
            )
            return

        # Extract and validate conversation_id
        conversation_id_raw = payload.get("conversation_id")
        if not conversation_id_raw:
            raise ValueError(f"Missing 'conversation_id' in event payload for event {envelope.id}.")

        conversation_id = (
            conversation_id_raw
            if isinstance(conversation_id_raw, UUID)
            else UUID(str(conversation_id_raw))
        )

        # Retrieve conversation history
        with self._unit_of_work as uow:
            conversation = uow.conversations.get(conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")

            messages = [
                {"role": msg.role.value, "content": msg.content} for msg in conversation.messages
            ]

        # Stream / generate LLM response tokens
        logger.info(
            "Invoking LLM completion for conversation %s with %d history messages.",
            conversation_id,
            len(messages),
        )
        tokens: list[str] = []
        async for token in self._llm_client.stream_chat(messages=messages):
            tokens.append(token)

        assistant_response = "".join(tokens)

        # Persist assistant response through CQRS command handler
        command = AppendAssistantMessageCommand(
            conversation_id=conversation_id,
            content=assistant_response,
        )
        self._append_handler.handle(command)

        logger.info(
            "Successfully appended assistant response for conversation %s.",
            conversation_id,
        )

    async def __call__(self, envelope: EventEnvelope) -> None:
        """Allow direct callable invocation satisfying EventHandler protocol."""
        await self.handle(envelope)
