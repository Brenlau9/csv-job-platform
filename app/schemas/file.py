from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileUploadResponse(BaseModel):
    id: int
    user_id: int
    original_filename: str
    stored_path: str
    size_bytes: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
