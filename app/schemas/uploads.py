from pydantic import BaseModel


class SingleUploadResponse(BaseModel):
    id: str
    original_filename: str
    content_type: str | None
    size_bytes: int


class MultiUploadResponse(BaseModel):
    uploads: list[SingleUploadResponse]
