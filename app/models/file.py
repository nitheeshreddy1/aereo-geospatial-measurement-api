from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_crs: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    measurement_crs: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    features: Mapped[list["FeatureRecord"]] = relationship(back_populates="file", cascade="all, delete-orphan")
