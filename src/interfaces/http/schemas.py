from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    id: UUID
    title: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000, description="Message content")


class MessageResponse(BaseModel):
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime
