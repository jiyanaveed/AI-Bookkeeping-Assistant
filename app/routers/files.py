"""Upload and download: local disk (dev) or Supabase Storage when SUPABASE_* env is set."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.deps.auth_session import assert_path_user_matches
from app.models.db_models import Upload, User
from app.schemas.uploads import MultiUploadResponse, SingleUploadResponse
from app.services.file_storage import read_upload_bytes, save_bytes

router = APIRouter(tags=["files"])


def _ensure_user(db: Session, user_id: str) -> None:
    if db.get(User, user_id) is None:
        u = User(id=user_id)
        db.add(u)
        db.commit()


@router.post("/v1/uploads", response_model=MultiUploadResponse)
async def upload_files(
    files: Annotated[list[UploadFile], File()],
    user_id: str = Form(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(None),
) -> MultiUploadResponse:
    assert_path_user_matches(user_id, db, authorization)
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded.")
    _ensure_user(db, user_id)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    results: list[SingleUploadResponse] = []
    for f in files:
        body = await f.read()
        if len(body) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {f.filename!r} exceeds max_upload_mb={settings.max_upload_mb}.",
            )
        row = Upload(
            user_id=user_id,
            original_filename=f.filename or "unnamed",
            content_type=f.content_type,
            size_bytes=len(body),
            storage_rel_path="",  # set after we have id
        )
        db.add(row)
        db.flush()
        rel, provider = save_bytes(
            settings,
            user_id=user_id,
            upload_id=row.id,
            original_filename=row.original_filename,
            body=body,
            content_type=row.content_type,
        )
        row.storage_rel_path = rel
        row.storage_provider = provider
        db.commit()
        db.refresh(row)
        results.append(
            SingleUploadResponse(
                id=row.id,
                original_filename=row.original_filename,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
            )
        )
    return MultiUploadResponse(uploads=results)


@router.get("/v1/files/{file_id}/content")
def download_file(
    file_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(None),
) -> Response:
    assert_path_user_matches(user_id, db, authorization)
    row = db.get(Upload, file_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    try:
        data = read_upload_bytes(settings, row)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.") from None
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return Response(
        content=data,
        media_type=row.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{row.original_filename}"',
        },
    )
