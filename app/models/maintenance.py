from __future__ import annotations

from datetime import date
from typing import List

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, Date, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class MaintenanceTypeEnum(str, PyEnum):
    OIL_CHANGE = "oil_change"
    TIRE_ROTATION = "tire_rotation"
    BRAKE_SERVICE = "brake_service"
    INSPECTION = "inspection"
    REPAIR = "repair"
    CLEANING = "cleaning"


class Maintenance(Base, TimestampMixin):
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), index=True)
    type: Mapped[MaintenanceTypeEnum] = mapped_column(SAEnum(MaintenanceTypeEnum))

    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    service_date: Mapped[date] = mapped_column(Date)
    next_service_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_out_of_service: Mapped[bool] = mapped_column(Boolean, default=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="maintenances")
