from datetime import datetime
from sqlalchemy.orm import Session

from app.models.file import FileRecord


class FileRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, filename: str, file_type: str, status: str = "PENDING") -> FileRecord:
        record = FileRecord(filename=filename, file_type=file_type, status=status)
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, record_id: str) -> FileRecord | None:
        return self.session.query(FileRecord).filter(FileRecord.id == record_id).first()

    def update_status(self, record: FileRecord, *, status: str, source_crs: str | None = None, measurement_crs: str | None = None, feature_count: int | None = None, error_message: str | None = None) -> FileRecord:
        record.status = status
        if source_crs is not None:
            record.source_crs = source_crs
        if measurement_crs is not None:
            record.measurement_crs = measurement_crs
        if feature_count is not None:
            record.feature_count = feature_count
        if error_message is not None:
            record.error_message = error_message
        record.processed_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(record)
        return record
