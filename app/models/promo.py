from __future__ import annotations

from datetime import date
from typing import List

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, Date, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class DiscountTypeEnum(str, PyEnum):
    PERCENT = "percent"
    FIXED = "fixed"


class Promo(Base, TimestampMixin):
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    discount_type: Mapped[DiscountTypeEnum] = mapped_column(SAEnum(DiscountTypeEnum))
    value: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)  # for fixed

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    min_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # simple link to bookings (applied promo code)
    bookings: Mapped[List["BookingPromo"]] = relationship(back_populates="promo", cascade="all, delete-orphan")


class BookingPromo(Base, TimestampMixin):
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo.id", ondelete="CASCADE"), index=True)
    amount_discounted: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    promo: Mapped["Promo"] = relationship(back_populates="bookings")
