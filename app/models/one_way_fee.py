from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, Boolean, UniqueConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class OneWayFee(Base, TimestampMixin):
    """One-way rental fees when pickup and dropoff locations differ."""
    __tablename__ = "one_way_fees"
    
    __table_args__ = (
        UniqueConstraint("from_location_id", "to_location_id", name="uq_one_way_fee_locations"),
    )

    from_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("location.id", ondelete="CASCADE"), nullable=False, index=True)
    to_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("location.id", ondelete="CASCADE"), nullable=False, index=True)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    from_location = relationship("Location", foreign_keys=[from_location_id], lazy="joined")
    to_location = relationship("Location", foreign_keys=[to_location_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<OneWayFee location {self.from_location_id} -> {self.to_location_id}: {self.fee_amount} {self.currency}>"
