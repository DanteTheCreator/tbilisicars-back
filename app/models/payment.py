from __future__ import annotations

from datetime import datetime

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class PaymentMethodEnum(str, PyEnum):
    CARD = "CARD"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    STRIPE = "STRIPE"
    PAYPAL = "PAYPAL"


class PaymentStatusEnum(str, PyEnum):
    UNPAID = "UNPAID"
    HALF = "HALF"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Payment(Base, TimestampMixin):
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"), index=True)

    method: Mapped[PaymentMethodEnum] = mapped_column(SAEnum(PaymentMethodEnum))
    status: Mapped[PaymentStatusEnum] = mapped_column(SAEnum(PaymentStatusEnum))

    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processor_response: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="payments")
    user: Mapped["User"] = relationship(back_populates="payments")
