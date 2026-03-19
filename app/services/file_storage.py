from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()
ALLOWED_CONTENT_TYPES = {
    "application/csv",
    "application/vnd.ms-excel",
    "text/csv",
}


def get_upload_dir() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_csv_upload(upload: UploadFile, content: bytes) -> None:
    filename = upload.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are allowed",
        )

    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type for CSV upload",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {settings.max_upload_size_bytes} bytes",
        )


def save_upload_file(upload: UploadFile, content: bytes) -> tuple[str, int]:
    upload_dir = get_upload_dir()
    filename = upload.filename or "upload.csv"
    stored_name = f"{uuid4().hex}_{Path(filename).name}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(content)
    return str(stored_path), len(content)
