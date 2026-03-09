from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from datetime import date

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, UniqueConstraint, Boolean, Date, Numeric, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .vehicle_model import VehicleModel
    from .location import Location
    from .vehicle_group import VehicleGroup
    from .vehicle_price import VehiclePrice
    from .booking import Booking
    from .damages import DamageReport
    from .documents import VehicleDocument
    from .vehicle_photos import VehiclePhoto
    from .vehicle_history import VehicleHistory
    from .maintenance import MaintenanceService
    from .partner import Partner


class VehicleStatusEnum(str, PyEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    IN_MAINTENANCE = "IN_MAINTENANCE"


class FuelTypeEnum(str, PyEnum):
    PETROL = "PETROL"
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

    # Foreign Keys
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_group_id: Mapped[int | None] = mapped_column(ForeignKey("vehiclegroup.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_model_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_model.id", ondelete="SET NULL"), nullable=True, index=True)

    # Vehicle Identification
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True)
    license_plate: Mapped[str] = mapped_column(String(20), index=True)
    tech_passport: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Legacy fields - kept for backward compatibility, will be deprecated
    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Vehicle Specifics
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
    vehicle_model: Mapped[Optional["VehicleModel"]] = relationship("VehicleModel", back_populates="vehicles")
    location: Mapped[Optional["Location"]] = relationship(back_populates="vehicles")
    vehicle_group: Mapped[Optional["VehicleGroup"]] = relationship(back_populates="vehicles")
    prices: Mapped[List["VehiclePrice"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    bookings: Mapped[List["Booking"]] = relationship(back_populates="vehicle")
    booking_assignments: Mapped[List["BookingVehicleAssignment"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    damages: Mapped[List["DamageReport"]] = relationship(back_populates="vehicle")
    documents: Mapped[List["VehicleDocument"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    photos: Mapped[List["VehiclePhoto"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan", order_by="VehiclePhoto.display_order")
    history: Mapped[List["VehicleHistory"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    maintenance_services: Mapped[List["MaintenanceService"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    partners: Mapped[List["Partner"]] = relationship(
        "Partner",
        secondary="partner_vehicle",
        back_populates="vehicles"
    )

    @hybrid_property
    def brand_name(self) -> str | None:
        """Get brand name from related model, or fallback to legacy make field"""
        if self.vehicle_model and self.vehicle_model.brand:
            return self.vehicle_model.brand.name
        return self.make

    @hybrid_property
    def model_name(self) -> str | None:
        """Get model name from related model, or fallback to legacy model field"""
        if self.vehicle_model:
            return self.vehicle_model.name
        return self.model

    @hybrid_property
    def computed_status(self) -> str:
        """Compute vehicle status based on active bookings"""
        # Check for active bookings (not RETURNED or CANCELED)
        print(f"[DEBUG] Vehicle {self.id} - Total bookings: {len(self.bookings)}")
        active_bookings = [b for b in self.bookings if b.status in ('PENDING', 'CONFIRMED', 'DELIVERED')]
        print(f"[DEBUG] Vehicle {self.id} - Active bookings: {len(active_bookings)}")
        
        if not active_bookings:
            return 'AVAILABLE'
        
        # Return status of most recent active booking (by pickup date)
        latest_booking = max(active_bookings, key=lambda b: b.pickup_datetime)
        print(f"[DEBUG] Vehicle {self.id} - Status: {latest_booking.status}")
        return latest_booking.status
