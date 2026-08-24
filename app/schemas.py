import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocumentStatus


class DocumentCreated(BaseModel):
    id: uuid.UUID
    status: DocumentStatus


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    uploaded_at: datetime


class DocumentRead(DocumentListItem):
    error_message: str | None
    page_count: int | None
    chunk_count: int | None
    doc_metadata: dict
    processed_at: datetime | None


class DocumentPage(BaseModel):
    items: list[DocumentListItem]
    total: int
    limit: int
    offset: int
