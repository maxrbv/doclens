import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.models import DocumentStatus


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: SecretStr = Field(min_length=1, max_length=256)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool


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
