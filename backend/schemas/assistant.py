
"""
schemas/assistant.py

Request / response models for the AI Assistant endpoints.
Dates are returned as ISO strings exactly as Supabase sends them.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    # Empty messages are allowed so users can upload a file
    # without typing a message.
    message: str = Field(default="", max_length=8000)

    conversation_id: str | None = None   # omit to start a new conversation

    # Files attached to this message.
    file_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
class RegisterFileRequest(BaseModel):
    """
    Sent by the frontend AFTER it has uploaded the file straight to the
    'assistant-files' bucket. storage_path must be '<user_id>/<something>'.
    """
    storage_path: str = Field(..., min_length=3, max_length=500)
    name: str = Field(..., min_length=1, max_length=255)
    mime_type: str | None = None
    size_bytes: int = Field(..., ge=0)
    conversation_id: str | None = None


class FileOut(BaseModel):
    id: str
    name: str
    mime_type: str | None = None
    size_bytes: int | None = None
    is_generated: bool = False
    conversation_id: str | None = None
    created_at: str | None = None


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int


# ---------------------------------------------------------------------------
# Conversations / history
# ---------------------------------------------------------------------------
class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class MessageOut(BaseModel):
    id: str
    role: str                       # 'user' or 'assistant' (tool messages are hidden)
    content: str | None = None
    file_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None


class ConversationDetail(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]
