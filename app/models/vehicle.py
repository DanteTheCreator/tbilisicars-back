from __future__ import annotations

from typing import List, Optional
from datetime import date

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, UniqueConstraint, Boolean, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class VehicleStatusEnum(str, PyEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    IN_MAINTENANCE = "IN_MAINTENANCE"


class FuelTypeEnum(str, PyEnum):
    GASOLINE = "GASOLINE"
    DIESEL = "DIESEL"
    HYBRID = "HYBRID"
    ELECTRIC = "ELECTRIC"


class TransmissionEnum(str, PyEnum):
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class VehicleClassEnum(str, PyEnum):
    ECONOMY = "ECONOMY"
    COMPACT = "COMPACT"
    MIDSIZE = "MIDSIZE"
    STANDARD = "STANDARD"
    FULLSIZE = "FULLSIZE"
    PREMIUM = "PREMIUM"
    LUXURY = "LUXURY"
    SUV = "SUV"
    MINIVAN = "MINIVAN"
    VAN = "VAN"
    TRUCK = "TRUCK"


class Vehicle(Base, TimestampMixin):
    __table_args__ = (
        UniqueConstraint("vin", name="uq_vehicle_vin"),
        UniqueConstraint("license_plate", name="uq_vehicle_plate"),
    )

    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_group_id: Mapped[int | None] = mapped_column(ForeignKey("vehiclegroup.id", ondelete="SET NULL"), nullable=True, index=True)

    vin: Mapped[str | None] = mapped_column(String(17), nullable=True)
    license_plate: Mapped[str] = mapped_column(String(20), index=True)
    tech_passport: Mapped[str | None] = mapped_column(String(50), nullable=True)

    make: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)

    vehicle_class: Mapped[VehicleClassEnum] = mapped_column(SAEnum(VehicleClassEnum), index=True)
    fuel_type: Mapped[FuelTypeEnum] = mapped_column(SAEnum(FuelTypeEnum))
    transmission: Mapped[TransmissionEnum] = mapped_column(SAEnum(TransmissionEnum))
    seats: Mapped[int] = mapped_column(Integer)
    doors: Mapped[int] = mapped_column(Integer)
    mileage: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[VehicleStatusEnum] = mapped_column(SAEnum(VehicleStatusEnum), index=True, default=VehicleStatusEnum.AVAILABLE)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    starting_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, default=50.00)

    registration_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    inspection_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relations
    # Use Optional string forward ref to satisfy SQLAlchemy's de-stringifier
    location: Mapped[Optional["Location"]] = relationship(back_populates="vehicles")
    vehicle_group: Mapped[Optional["VehicleGroup"]] = relationship(back_populates="vehicles")
    prices: Mapped[List["VehiclePrice"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    bookings: Mapped[List["Booking"]] = relationship(back_populates="vehicle")
    damages: Mapped[List["DamageReport"]] = relationship(back_populates="vehicle")
    documents: Mapped[List["VehicleDocument"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    photos: Mapped[List["VehiclePhoto"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan", order_by="VehiclePhoto.display_order")
