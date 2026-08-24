import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings


class StoragePathError(ValueError):
    pass


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


async def save(content: AsyncIterator[bytes], relative_path: str) -> int:
    target = _resolve(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.part")
    size = 0
    try:
        with tmp.open("wb") as handle:
            async for chunk in content:
                size += len(chunk)
                handle.write(chunk)
        tmp.replace(target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise

    return size


def open_stream(relative_path: str) -> BinaryIO:
    return _resolve(relative_path).open("rb")


def delete(relative_path: str) -> None:
    _resolve(relative_path).unlink(missing_ok=True)


def exists(relative_path: str) -> bool:
    return _resolve(relative_path).is_file()
