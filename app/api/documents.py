from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.core.broker import publish_document_task
from app.schemas import DocumentCreated
from app.services.documents import (
    EmptyFile,
    FileTooLarge,
    UnsupportedFileType,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

CHUNK_SIZE = 1024 * 1024


async def _chunks(upload: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await upload.read(CHUNK_SIZE):
        yield chunk


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload(
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
) -> DocumentCreated:
    try:
        document, created = await upload_document(
            session,
            original_filename=file.filename or "unnamed",
            stream=_chunks(file),
            max_bytes=settings.max_upload_bytes,
            publish=publish_document_task,
        )
    except EmptyFile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Файл пуст",
        ) from None
    except FileTooLarge:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл больше {settings.max_upload_mb} МБ",
        ) from None
    except UnsupportedFileType:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Поддерживаются только PDF и DOCX",
        ) from None

    if not created:
        response.status_code = status.HTTP_200_OK

    return DocumentCreated(id=document.id, status=document.status)
