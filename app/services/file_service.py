from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import shutil
import tempfile

from fastapi import UploadFile
from pyproj import CRS
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.feature_repository import FeatureRepository
from app.repositories.file_repository import FileRepository
from app.services.geospatial_service import GeospatialService
from app.utils.validation import ApiError, validate_filename, validate_upload_size

logger = get_logger(__name__)


class FileService:
    def __init__(self, session: Session):
        self.session = session
        self.file_repository = FileRepository(session)
        self.feature_repository = FeatureRepository(session)
        self.geospatial_service = GeospatialService()

    async def process_upload(self, upload: UploadFile):
        filename = validate_filename(upload.filename)
        temp_dir = Path(tempfile.mkdtemp(prefix="aereo_upload_"))
        temp_file = temp_dir / "uploaded_file"
        total_bytes = 0

        try:
            with open(temp_file, "wb") as sink:
                while True:
                    chunk = await upload.read(65536)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise ApiError("FILE_TOO_LARGE", "The uploaded file exceeds the configured size limit.", 413)
                    sink.write(chunk)

            validate_upload_size(total_bytes)
            file_record = self.file_repository.create(filename, Path(filename).suffix.lower().lstrip("."), status="PROCESSING")
            logger.info("UPLOAD_RECEIVED", extra={"record_id": file_record.id, "uploaded_name": filename})

            try:
                gdf = self.geospatial_service.read_geometry_file(filename, temp_file)
                features, source_crs, measurement_crs = self.geospatial_service.extract_features(gdf)
                file_record.source_crs = source_crs
                file_record.measurement_crs = measurement_crs
                file_record.feature_count = len(features)
                file_record.status = "PROCESSING"

                for feature in features:
                    geom_srid = 4326
                    try:
                        source_crs = feature.get("source_crs") or file_record.source_crs
                        if source_crs:
                            geom_srid = CRS.from_user_input(source_crs).to_epsg() or 4326
                    except Exception:
                        geom_srid = 4326
                    stored_feature = self.feature_repository.add_feature(
                        file_id=file_record.id,
                        feature_index=feature["feature_id"],
                        geometry_type=feature["geometry_type"],
                        geometry=feature["geometry"],
                        properties=feature["properties"],
                        source_geometry=feature.get("source_geometry"),
                        geom_srid=geom_srid,
                    )
                    measurement_payload = feature["measurement"]
                    if measurement_payload is not None:
                        self.feature_repository.add_measurement(
                            feature_id=stored_feature.id,
                            measurement_type=measurement_payload["type"],
                            value=measurement_payload["value"],
                            unit=measurement_payload["unit"],
                        )

                file_record.status = "COMPLETED"
                file_record.processed_at = datetime.utcnow()
                file_record.error_message = None
                self.session.commit()
                logger.info("MEASUREMENT_COMPLETED", extra={"record_id": file_record.id, "feature_count": len(features)})
                return file_record
            except ApiError as exc:
                self.session.rollback()
                file_record.status = "FAILED"
                file_record.error_message = exc.message
                file_record.processed_at = datetime.utcnow()
                self.session.commit()
                logger.warning("VALIDATION_FAILED", extra={"record_id": file_record.id, "error_message": exc.message})
                raise
            except Exception as exc:  # pragma: no cover
                self.session.rollback()
                file_record.status = "FAILED"
                file_record.error_message = str(exc)
                file_record.processed_at = datetime.utcnow()
                self.session.commit()
                logger.exception("PROCESSING_FAILED", extra={"record_id": file_record.id})
                raise ApiError("CORRUPTED_GEOSPATIAL_FILE", "The geospatial file could not be processed.", 500)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
