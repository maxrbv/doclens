import hashlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings

TEMP_DIR = ".tmp"


class StoragePathError(ValueError):
    pass


@dataclass(frozen=True)
class StagedFile:
    path: Path
    size_bytes: int
    checksum: str


def _root() -> Path:
    return get_settings().storage_path.resolve()


def build_relative_path(checksum: str, extension: str) -> str:
    if len(checksum) < 4:
        raise StoragePathError("checksum слишком короткий для раскладки по каталогам")
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{checksum[:2]}/{checksum[2:4]}/{checksum}{suffix}"


def _resolve(relative_path: str) -> Path:
    root = _root()
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root):
        raise StoragePathError("путь выходит за пределы хранилища")
    return target


async def stage(content: AsyncIterator[bytes]) -> StagedFile:
    temp_dir = _root() / TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"{uuid.uuid4().hex}.part"

    hasher = hashlib.sha256()
    size = 0
    try:
        with path.open("wb") as handle:
            async for chunk in content:
                size += len(chunk)
                hasher.update(chunk)
                handle.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return StagedFile(path=path, size_bytes=size, checksum=hasher.hexdigest())


def commit_staged(staged: StagedFile, relative_path: str) -> None:
    target = _resolve(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged.path.replace(target)


def discard_staged(staged: StagedFile) -> None:
    staged.path.unlink(missing_ok=True)


def open_stream(relative_path: str) -> BinaryIO:
    return _resolve(relative_path).open("rb")


def delete(relative_path: str) -> None:
    _resolve(relative_path).unlink(missing_ok=True)


def exists(relative_path: str) -> bool:
    return _resolve(relative_path).is_file()
