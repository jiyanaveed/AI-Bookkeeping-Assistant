"""Conversation + message history for internal UI (read-only; chat POST still drives agent)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.models.db_models import Conversation, Message, MessageAttachment
from app.schemas.conversations import AttachmentRef, ConversationSummary, MessageRead

router = APIRouter(tags=["conversations"])


@router.get("/v1/conversations", response_model=list[ConversationSummary])
def list_conversations(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> list[ConversationSummary]:
    assert_path_user_matches(user_id, db, authorization)
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(100)
        .all()
    )
    if not rows:
        return []
    ids = [r.id for r in rows]
    counts = dict(
        db.query(Message.conversation_id, func.count(Message.id))
        .filter(Message.conversation_id.in_(ids))
        .group_by(Message.conversation_id)
        .all()
    )
    out: list[ConversationSummary] = []
    for c in rows:
        out.append(
            ConversationSummary(
                id=c.id,
                user_id=c.user_id,
                channel=c.channel,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=int(counts.get(c.id, 0)),
            )
        )
    return out


@router.get("/v1/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def get_messages(
    conversation_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> list[MessageRead]:
    assert_path_user_matches(user_id, db, authorization)
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .options(joinedload(Message.file_links).joinedload(MessageAttachment.upload))
        .all()
    )
    out: list[MessageRead] = []
    for m in rows:
        att = [
            AttachmentRef(
                file_id=link.upload.id,
                filename=link.upload.original_filename,
                content_type=link.upload.content_type,
            )
            for link in m.file_links
        ]
        out.append(
            MessageRead(
                id=m.id,
                conversation_id=m.conversation_id,
                sender_type=m.sender_type,
                agent_name=m.agent_name,
                message_text=m.message_text,
                created_at=m.created_at,
                attachments=att,
                intent=m.intent,
            )
        )
    return out
