from __future__ import annotations

from typing import List
from datetime import date

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, Numeric, Date, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CurrencyEnum(str, PyEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    GEL = "GEL"


class PriceTypeEnum(str, PyEnum):
    BASE_DAILY = "base_daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKEND = "weekend"
    SEASONAL = "seasonal"
    ONE_WAY_FEE = "one_way_fee"


class VehiclePrice(Base, TimestampMixin):
    __table_args__ = (
        UniqueConstraint("vehicle_id", "price_type", "start_date", "end_date", name="uq_vehicle_price_range"),
    )

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), index=True)
    price_type: Mapped[PriceTypeEnum] = mapped_column(SAEnum(PriceTypeEnum), index=True)

    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[CurrencyEnum] = mapped_column(SAEnum(CurrencyEnum), default=CurrencyEnum.USD)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="prices")
