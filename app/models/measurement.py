from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeasurementRecord(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint("feature_id", "measurement_type", name="uq_feature_measurement_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("features.id"), nullable=False, index=True)
    measurement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)

    feature: Mapped["FeatureRecord"] = relationship(back_populates="measurements")
