from __future__ import annotations

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class DocumentTypeEnum(str, PyEnum):
    REGISTRATION = "registration"
    INSURANCE = "insurance"
    INSPECTION = "inspection"
    OTHER = "other"


class VehicleDocument(Base, TimestampMixin):
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), index=True)

    type: Mapped[DocumentTypeEnum] = mapped_column(SAEnum(DocumentTypeEnum))
    title: Mapped[str] = mapped_column(String(150))
    file_path: Mapped[str] = mapped_column(String(500))

    vehicle: Mapped["Vehicle"] = relationship(back_populates="documents")
