from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base

GEOM_COLUMN_TYPE = Geometry(geometry_type="GEOMETRY", srid=-1, spatial_index=True, dimension=2) if settings.DATABASE_URL.startswith("postgresql") else JSON


class FeatureRecord(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("file_id", "feature_index", name="uq_file_feature_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False, index=True)
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    geometry_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    geom: Mapped[object | None] = mapped_column(GEOM_COLUMN_TYPE, nullable=True)

    file: Mapped["FileRecord"] = relationship(back_populates="features")
    measurements: Mapped[list["MeasurementRecord"]] = relationship(back_populates="feature", cascade="all, delete-orphan")
