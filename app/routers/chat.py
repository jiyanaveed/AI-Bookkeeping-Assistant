from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import process_chat
from app.services.chat_timing import ChatTiming

router = APIRouter(tags=["chat"])


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> ChatResponse:
    assert_path_user_matches(payload.user_id, db, authorization)
    settings = get_settings()
    timing = ChatTiming()
    timing.event("request_received")
    out = await process_chat(
        db,
        settings,
        message=payload.message,
        user_id=payload.user_id,
        conversation_id=payload.conversation_id,
        attachment_ids=payload.attachment_ids,
        message_intent=payload.message_intent,
        timing=timing,
    )
    timing.event("response_sent", total_ms=round(timing.total_ms(), 3))
    return ChatResponse(
        reply=out.reply,
        user_id=out.user_id,
        conversation_id=out.conversation_id,
    )
