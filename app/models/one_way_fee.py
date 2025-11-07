from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class OneWayFee(Base, TimestampMixin):
    """One-way rental fees when pickup and dropoff cities differ."""
    __tablename__ = "one_way_fees"
    
    __table_args__ = (
        UniqueConstraint("from_city", "to_city", name="uq_one_way_fee_cities"),
    )

    from_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    to_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<OneWayFee {self.from_city} -> {self.to_city}: {self.fee_amount} {self.currency}>"
