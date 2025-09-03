from __future__ import annotations

from typing import List

from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Location(Base, TimestampMixin):
    name: Mapped[str] = mapped_column(String(150), index=True)
    address_line1: Mapped[str] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relations
    pickup_bookings: Mapped[List["Booking"]] = relationship(back_populates="pickup_location", foreign_keys="Booking.pickup_location_id")
    dropoff_bookings: Mapped[List["Booking"]] = relationship(back_populates="dropoff_location", foreign_keys="Booking.dropoff_location_id")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="location")
