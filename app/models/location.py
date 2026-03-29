from __future__ import annotations

import enum
from typing import List

from sqlalchemy import String, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class LocationType(str, enum.Enum):
    meet_and_greet = "meet_and_greet"
    rental_office = "rental_office"


class Location(Base, TimestampMixin):
    name: Mapped[str] = mapped_column(String(150), index=True)
    address_line1: Mapped[str] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, name="location_type_enum"),
        default=LocationType.meet_and_greet,
        server_default="meet_and_greet",
    )

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relations
    pickup_bookings: Mapped[List["Booking"]] = relationship(back_populates="pickup_location", foreign_keys="Booking.pickup_location_id")
    dropoff_bookings: Mapped[List["Booking"]] = relationship(back_populates="dropoff_location", foreign_keys="Booking.dropoff_location_id")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="location")
