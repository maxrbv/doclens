import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

__all__ = ["Base", "Chunk", "Document", "DocumentStatus", "QueryLog", "QueryMode"]


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class QueryMode(StrEnum):
    BM25 = "bm25"
    KNN = "knn"
    RRF = "rrf"
    ASK = "ask"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'done', 'failed')",
            name="status_valid",
        ),
        Index("ix_documents_status", "status"),
        Index("ix_documents_uploaded_at", "uploaded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    storage_path: Mapped[str] = mapped_column(String(512))

    status: Mapped[str] = mapped_column(String(16), default=DocumentStatus.PROCESSING)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    chunk_count: Mapped[int | None] = mapped_column(Integer, default=None)
    doc_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer)

    text: Mapped[str] = mapped_column(Text)
    heading_path: Mapped[list] = mapped_column(JSONB, default=list)
    anchor: Mapped[dict] = mapped_column(JSONB, default=dict)
    token_count: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


class QueryLog(Base):
    __tablename__ = "query_logs"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('bm25', 'knn', 'rrf', 'ask')",
            name="mode_valid",
        ),
        Index("ix_query_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    query_text: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(8))
    latency_ms: Mapped[int] = mapped_column(Integer)
    top_chunk_ids: Mapped[list] = mapped_column(JSONB, default=list)

    answer_text: Mapped[str | None] = mapped_column(Text, default=None)
    llm_provider: Mapped[str | None] = mapped_column(String(32), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
