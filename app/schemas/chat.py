from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1, max_length=36)
    conversation_id: str | None = Field(None, max_length=36)
    attachment_ids: list[str] = Field(default_factory=list)
    message_intent: str | None = Field(
        None,
        max_length=64,
        description="Optional: spending marks the message for bookkeeping flow.",
    )


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    conversation_id: str
