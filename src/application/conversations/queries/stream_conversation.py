"""Stream conversation query and handler for reactive AI responses."""

import inspect
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepositoryPort,
)
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.domain_error import DomainError


@dataclass(frozen=True)
class StreamConversationQuery:
    """Query DTO for requesting an AI completion stream for a conversation."""

    conversation_id: UUID
    temperature: float = 0.7
    max_tokens: int = 1000

    def __post_init__(self) -> None:
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0.")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be greater than 0.")


class StreamConversationQueryHandler:
    """Application use case for orchestrating LLM response streaming."""

    def __init__(
        self,
        conversation_repository: ConversationRepositoryPort | None = None,
        llm_client: LlmClientPort | None = None,
        *,
        unit_of_work: UnitOfWorkPort | None = None,
    ) -> None:
        if conversation_repository is None and unit_of_work is not None:
            conversation_repository = unit_of_work.conversations

        if conversation_repository is None:
            raise ValueError("Either conversation_repository or unit_of_work must be provided.")
        if llm_client is None:
            raise ValueError("llm_client must be provided.")

        self._repository = conversation_repository
        self._llm_client = llm_client

    async def handle(self, query: StreamConversationQuery) -> AsyncIterator[str]:
        """Stream real-time LLM token chunks for a given conversation query.

        Args:
            query: StreamConversationQuery containing conversation ID and sampling params.

        Returns:
            AsyncIterator of token chunks streamed from the LLM provider.

        Raises:
            ConversationNotFoundError: If target conversation does not exist.
            DomainError: If conversation is empty or last message was not from user.
        """
        conversation = self._repository.get(query.conversation_id)

        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {query.conversation_id} not found.")

        if not conversation.messages:
            raise DomainError("Cannot stream response for a conversation with no messages.")

        if conversation.messages[-1].role != MessageRole.USER:
            raise DomainError("Cannot stream response when the last message is not from user.")

        formatted_messages = [
            {"role": msg.role.value, "content": msg.content} for msg in conversation.messages
        ]

        stream_or_coroutine = self._llm_client.stream_chat(
            messages=formatted_messages,
            temperature=query.temperature,
            max_tokens=query.max_tokens,
        )

        if inspect.isawaitable(stream_or_coroutine):
            return await stream_or_coroutine  # type: ignore[no-any-return]

        return stream_or_coroutine


# Alias for naming consistency with CQRS templates
StreamConversationHandler = StreamConversationQueryHandler
