from typing import Any

from pydantic import BaseModel


class MeasurementResult(BaseModel):
    type: str | None = None
    value: float | None = None
    unit: str | None = None


class FeatureMeasurementResponse(BaseModel):
    feature_id: int
    geometry_type: str
    geometry: dict[str, Any]
    properties: dict[str, Any]
    measurement: MeasurementResult | None


class FileMeasurementsResponse(BaseModel):
    file_id: str
    measurements: list[FeatureMeasurementResponse]
