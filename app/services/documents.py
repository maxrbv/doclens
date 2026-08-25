import logging
import uuid
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.services import storage

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

EXTENSIONS = {PDF_MIME: ".pdf", DOCX_MIME: ".docx"}

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"

PublishTask = Callable[[uuid.UUID], Awaitable[None]]


class UploadError(Exception):
    pass


class EmptyFile(UploadError):
    pass


class FileTooLarge(UploadError):
    pass


class UnsupportedFileType(UploadError):
    pass


def detect_mime(path: Path) -> str | None:
    with path.open("rb") as handle:
        head = handle.read(8)

    if head.startswith(_PDF_MAGIC):
        return PDF_MIME

    if head.startswith(_ZIP_MAGIC):
        try:
            with zipfile.ZipFile(path) as archive:
                if "word/document.xml" in archive.namelist():
                    return DOCX_MIME
        except zipfile.BadZipFile:
            return None

    return None


async def _limited(stream: AsyncIterator[bytes], max_bytes: int) -> AsyncIterator[bytes]:
    total = 0
    async for chunk in stream:
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLarge
        yield chunk


async def upload_document(
    session: AsyncSession,
    *,
    original_filename: str,
    stream: AsyncIterator[bytes],
    max_bytes: int,
    publish: PublishTask,
) -> tuple[Document, bool]:
    staged = await storage.stage(_limited(stream, max_bytes))
    committed = False

    try:
        if staged.size_bytes == 0:
            raise EmptyFile

        mime_type = detect_mime(staged.path)
        if mime_type is None:
            raise UnsupportedFileType

        existing = await session.scalar(
            select(Document).where(Document.checksum == staged.checksum)
        )
        if existing is not None:
            return existing, False

        relative_path = storage.build_relative_path(staged.checksum, EXTENSIONS[mime_type])
        document = Document(
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=staged.size_bytes,
            checksum=staged.checksum,
            storage_path=relative_path,
        )
        session.add(document)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(
                select(Document).where(Document.checksum == staged.checksum)
            )
            if existing is None:
                raise
            return existing, False

        storage.commit_staged(staged, relative_path)
        committed = True
    finally:
        if not committed:
            storage.discard_staged(staged)

    try:
        await publish(document.id)
    except Exception:
        logger.exception(
            "failed to publish processing task",
            extra={"document_id": str(document.id)},
        )

    return document, True
