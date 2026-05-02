from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


ALLOWED_FILE_TYPES = {"pdf", "docx", "txt", "md", "markdown"}


def normalize_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix == "markdown":
        return "md"
    return suffix


def validate_file_type(filename: str) -> str:
    file_type = normalize_file_type(filename)
    if file_type not in ALLOWED_FILE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_FILE_TYPES))
        raise ValueError(f"Unsupported file type '{file_type}'. Allowed: {allowed}")
    return file_type


def build_stored_filename(original_filename: str) -> str:
    file_type = normalize_file_type(original_filename)
    return f"{uuid4().hex}.{file_type}"


async def save_upload_file(
    upload_file: UploadFile,
    destination: Path,
    max_size_mb: int,
) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    max_size_bytes = max_size_mb * 1024 * 1024
    total_size = 0

    with destination.open("wb") as out_file:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size_bytes:
                destination.unlink(missing_ok=True)
                raise ValueError(f"File exceeds max upload size of {max_size_mb} MB")
            out_file.write(chunk)

    return total_size
