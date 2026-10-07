import os
from pathlib import PurePosixPath

from app.core.config import settings


SUPPORTED_EXTENSIONS = {".kml", ".zip"}


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def validate_filename(filename: str | None) -> str:
    if not filename:
        raise ApiError("UNSUPPORTED_FILE_TYPE", "No filename was supplied.", 400)
    safe = os.path.basename(filename.replace("\\", "/"))
    if not safe or safe in {".", ".."}:
        raise ApiError("UNSUPPORTED_FILE_TYPE", "Filename is invalid.", 400)
    _, extension = os.path.splitext(safe)
    if extension.lower() not in SUPPORTED_EXTENSIONS:
        raise ApiError("UNSUPPORTED_FILE_TYPE", f"Unsupported file type: {extension or 'none'}", 400)
    return safe


def validate_upload_size(payload: bytes | int | None) -> None:
    size = len(payload) if isinstance(payload, (bytes, bytearray)) else payload
    if size is None or size == 0:
        raise ApiError("EMPTY_UPLOAD", "The uploaded file is empty.", 400)
    if size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ApiError("FILE_TOO_LARGE", "The uploaded file exceeds the configured size limit.", 413)


def sanitize_archive_member(member_name: str) -> str:
    posix_name = member_name.replace("\\", "/")
    pure_path = PurePosixPath(posix_name)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ApiError("INVALID_ZIP", "Zip archive contains unsafe paths.", 400)
    sanitized = "/".join(part for part in pure_path.parts if part not in (".", ""))
    if not sanitized:
        raise ApiError("INVALID_ZIP", "Zip archive contains an empty member name.", 400)
    if sanitized.startswith("/"):
        raise ApiError("INVALID_ZIP", "Zip archive contains an unsafe absolute path.", 400)
    return sanitized
