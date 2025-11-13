from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .booking import Booking
    from .admin import Admin


class BookingHistory(Base, TimestampMixin):
    """Track all changes to bookings for audit trail"""
    
    __tablename__ = "booking_history"
    
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Action types: CREATED, STATUS_CHANGED, VEHICLE_CHANGED, PAYMENT_UPDATED, etc.
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    
    # Field that was changed (optional)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Old and new values as text
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Human-readable description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="history")
    changed_by: Mapped["Admin | None"] = relationship("Admin")
