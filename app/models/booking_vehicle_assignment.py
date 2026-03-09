from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .booking import Booking
    from .vehicle import Vehicle
    from .location import Location


class BookingVehicleAssignment(Base, TimestampMixin):
    """
    Track vehicle assignments for bookings with date ranges.
    This allows tracking multiple vehicle changes during a booking's lifecycle.
    """
    __tablename__ = "booking_vehicle_assignments"

    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="RESTRICT"), index=True)
    
    # Date range when this vehicle was/is assigned to the booking
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # When vehicle is returned/changed
    return_location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("location.id", ondelete="SET NULL"), nullable=True)
    odometer_reading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="vehicle_assignments")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="booking_assignments")
    return_location: Mapped[Optional["Location"]] = relationship("Location")

    def __repr__(self) -> str:
        return f"<BookingVehicleAssignment(booking_id={self.booking_id}, vehicle_id={self.vehicle_id}, {self.start_date} - {self.end_date})>"
