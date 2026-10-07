from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.feature import FeatureRecord
from app.models.measurement import MeasurementRecord
from app.utils.geometry import normalize_geometry_for_storage


class FeatureRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_feature(self, file_id: str, feature_index: int, geometry_type: str, geometry: dict, properties: dict, source_geometry: dict | None = None, geom_srid: int = 4326) -> FeatureRecord:
        if source_geometry is None:
            source_geometry = geometry
        geom_value = None
        try:
            source_shape = shape(source_geometry)
            normalized_shape = normalize_geometry_for_storage(source_shape)
            if normalized_shape is not None:
                geom_value = from_shape(normalized_shape, srid=geom_srid)
        except Exception:
            geom_value = None
        stored_geom = geom_value if settings.DATABASE_URL.startswith("postgresql") else None
        record = FeatureRecord(
            file_id=file_id,
            feature_index=feature_index,
            geometry_type=geometry_type,
            geometry=geometry,
            properties=properties,
            geom=stored_geom,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def add_measurement(self, feature_id: int, measurement_type: str, value: float | None, unit: str | None) -> MeasurementRecord:
        record = MeasurementRecord(feature_id=feature_id, measurement_type=measurement_type, value=value, unit=unit)
        self.session.add(record)
        self.session.flush()
        return record

    def list_measurements_for_file(self, file_id: str):
        query = (
            self.session.query(FeatureRecord, MeasurementRecord)
            .join(MeasurementRecord, MeasurementRecord.feature_id == FeatureRecord.id)
            .filter(FeatureRecord.file_id == file_id)
            .all()
        )
        return query
