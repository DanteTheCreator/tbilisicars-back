from __future__ import annotations

from datetime import date
from typing import List

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, Date, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .booking import Booking


class DamageSeverityEnum(str, PyEnum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class DamageReport(Base, TimestampMixin):
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("booking.id", ondelete="SET NULL"), nullable=True)

    description: Mapped[str] = mapped_column(String(1000))
    severity: Mapped[DamageSeverityEnum] = mapped_column(SAEnum(DamageSeverityEnum))
    reported_date: Mapped[date] = mapped_column(Date)

    estimated_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="damages")
    booking: Mapped[Booking | None] = relationship(back_populates="damages")
