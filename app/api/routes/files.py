from fastapi import APIRouter, Depends, UploadFile, status
from fastapi import File as FastAPIFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.file import File
from app.models.user import User
from app.schemas.file import FileUploadResponse
from app.services.file_storage import save_upload_file, validate_csv_upload

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    upload: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> File:
    content = await upload.read()
    validate_csv_upload(upload, content)
    stored_path, size_bytes = save_upload_file(upload, content)

    db_file = File(
        user_id=current_user.id,
        original_filename=upload.filename or "upload.csv",
        stored_path=stored_path,
        size_bytes=size_bytes,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    await upload.close()
    return db_file
