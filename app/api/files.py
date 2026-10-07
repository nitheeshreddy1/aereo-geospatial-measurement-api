from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.file import FileRecord
from app.models.feature import FeatureRecord
from app.models.measurement import MeasurementRecord
from app.repositories.file_repository import FileRepository
from app.schemas.common import ErrorResponse, HealthResponse
from app.schemas.file import FileUploadResponse
from app.services.file_service import FileService
from app.utils.validation import ApiError

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok", "service": "aereo-geospatial-api"}


@router.get("/ready", response_model=HealthResponse)
def readiness() -> dict:
    return {"status": "ok", "service": "aereo-geospatial-api"}


@router.post("/api/files/", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    service = FileService(db)
    try:
        record = await service.process_upload(file)
    except ApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error": {"code": exc.code, "message": exc.message}})
    return {
        "id": record.id,
        "filename": record.filename,
        "file_type": record.file_type,
        "feature_count": record.feature_count,
        "source_crs": record.source_crs,
        "measurement_crs": record.measurement_crs,
        "status": record.status,
        "error_message": record.error_message,
        "created_at": record.created_at,
        "processed_at": record.processed_at,
    }


@router.get("/api/files/{file_id}/", response_model=FileUploadResponse)
def get_file(file_id: str, db: Session = Depends(get_db)):
    repository = FileRepository(db)
    record = repository.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "The requested file was not found."}})
    return {
        "id": record.id,
        "filename": record.filename,
        "file_type": record.file_type,
        "feature_count": record.feature_count,
        "source_crs": record.source_crs,
        "measurement_crs": record.measurement_crs,
        "status": record.status,
        "error_message": record.error_message,
        "created_at": record.created_at,
        "processed_at": record.processed_at,
    }


@router.get("/api/files/{file_id}/measurements/")
def get_measurements(file_id: str, db: Session = Depends(get_db)):
    repository = FileRepository(db)
    file_record = repository.get(file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "The requested file was not found."}})

    rows = (
        db.query(FeatureRecord, MeasurementRecord)
        .outerjoin(MeasurementRecord, MeasurementRecord.feature_id == FeatureRecord.id)
        .filter(FeatureRecord.file_id == file_id)
        .all()
    )
    measurements = []
    for feature, measurement in rows:
        measurement_payload = None
        if measurement is not None:
            measurement_payload = {
                "type": measurement.measurement_type,
                "value": measurement.value,
                "unit": measurement.unit,
                "valid": measurement.measurement_type != "invalid",
            }
            if measurement.measurement_type == "invalid":
                measurement_payload["reason"] = feature.properties.get("_invalid_reason", "Geometry is invalid.")
        measurements.append(
            {
                "feature_id": feature.feature_index,
                "geometry_type": feature.geometry_type,
                "geometry": feature.geometry,
                "properties": feature.properties,
                "measurement": measurement_payload,
            }
        )
    return {"file_id": file_id, "measurements": measurements}
