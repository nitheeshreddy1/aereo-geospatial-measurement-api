from pydantic import BaseModel


class MeasurementRecordSchema(BaseModel):
    measurement_type: str
    value: float | None = None
    unit: str | None = None
