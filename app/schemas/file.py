from datetime import datetime

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    feature_count: int = 0
    source_crs: str | None = None
    measurement_crs: str | None = None
    status: str = "PENDING"
    error_message: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None


class FileDetailResponse(FileUploadResponse):
    pass
