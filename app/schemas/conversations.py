from pydantic import BaseModel, Field


class AttachmentRef(BaseModel):
    file_id: str
    filename: str
    content_type: str | None


class MessageRead(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    agent_name: str | None
    message_text: str
    created_at: object
    attachments: list[AttachmentRef]
    intent: str | None = None


class ConversationSummary(BaseModel):
    id: str
    user_id: str
    channel: str
    created_at: object
    updated_at: object
    message_count: int


class UploadInfo(BaseModel):
    id: str
    original_filename: str
    content_type: str | None
    size_bytes: int
