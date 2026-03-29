from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from enum import Enum as PyEnum
from sqlalchemy import String, Enum as SAEnum, Integer, ForeignKey, DateTime, Date, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class BookingStatusEnum(str, PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"
    CANCELED = "CANCELED"
    NO_SHOW = "NO_SHOW"


class PaymentStatusEnum(str, PyEnum):
    UNPAID = "UNPAID"
    HALF = "HALF"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Booking(Base, TimestampMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"), index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle.id", ondelete="SET NULL"), index=True, nullable=True)
    vehicle_group_id: Mapped[int | None] = mapped_column(ForeignKey("vehiclegroup.id", ondelete="SET NULL"), index=True, nullable=True)
    vehicle_model_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_model.id", ondelete="SET NULL"), index=True, nullable=True)

    pickup_location_id: Mapped[int] = mapped_column(ForeignKey("location.id", ondelete="RESTRICT"))
    dropoff_location_id: Mapped[int] = mapped_column(ForeignKey("location.id", ondelete="RESTRICT"))

    pickup_datetime: Mapped[datetime] = mapped_column(DateTime)
    dropoff_datetime: Mapped[datetime] = mapped_column(DateTime)

    status: Mapped[BookingStatusEnum] = mapped_column(SAEnum(BookingStatusEnum), index=True, default=BookingStatusEnum.PENDING)
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(SAEnum(PaymentStatusEnum), index=True, default=PaymentStatusEnum.UNPAID)

    # Rate tracking - records which rate was used for pricing
    rate_id: Mapped[int | None] = mapped_column(ForeignKey("rate.id", ondelete="SET NULL"), index=True, nullable=True)
    rate_tier_id: Mapped[int | None] = mapped_column(ForeignKey("ratetier.id", ondelete="SET NULL"), index=True, nullable=True)
    price_per_day: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    base_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    taxes: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    fees: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    one_way_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    deposit: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Snapshot of contact information at time of booking (denormalized)
    contact_full_name: Mapped[str] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Broker information for bookings from partners (Discover Cars, VIPCars, etc.)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    broker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # External booking ID from broker
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partner.id", ondelete="SET NULL"), nullable=True, index=True)

    # Driver document details
    document_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'passport' or 'id'
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Amounts already present: total_amount and currency

    # Source of the booking: 'web', 'admin', or 'broker'
    source: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pickup_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    return_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Soft delete — set to a timestamp when deleted; never physically remove a booking row
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None, index=True)

    # Relations
    user: Mapped["User"] = relationship(back_populates="bookings")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="bookings")
    vehicle_group: Mapped["VehicleGroup"] = relationship("VehicleGroup", foreign_keys=[vehicle_group_id])
    vehicle_model: Mapped["VehicleModel"] = relationship("VehicleModel", foreign_keys=[vehicle_model_id])
    
    rate: Mapped["Rate"] = relationship("Rate", foreign_keys=[rate_id])
    rate_tier: Mapped["RateTier"] = relationship("RateTier", foreign_keys=[rate_tier_id])

    pickup_location: Mapped["Location"] = relationship(back_populates="pickup_bookings", foreign_keys=[pickup_location_id])
    dropoff_location: Mapped["Location"] = relationship(back_populates="dropoff_bookings", foreign_keys=[dropoff_location_id])
    
    partner: Mapped["Partner"] = relationship("Partner", back_populates="bookings", foreign_keys=[partner_id])

    extras: Mapped[List["BookingExtra"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    damages: Mapped[List["DamageReport"]] = relationship(back_populates="booking")
    photos: Mapped[List["BookingPhoto"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    # Do NOT use delete-orphan here — history must survive if the booking is ever hard-deleted
    history: Mapped[List["BookingHistory"]] = relationship(back_populates="booking", cascade="all", order_by="BookingHistory.changed_at.desc()")
    vehicle_assignments: Mapped[List["BookingVehicleAssignment"]] = relationship(back_populates="booking", cascade="all, delete-orphan", order_by="BookingVehicleAssignment.start_date")


class ExtraTypeEnum(str, PyEnum):
    GPS = "GPS"
    CHILD_SEAT = "CHILD_SEAT"
    EXTRA_DRIVER = "EXTRA_DRIVER"
    ROOF_RACK = "ROOF_RACK"
    WIFI = "WIFI"
    SNOW_CHAINS = "SNOW_CHAINS"


class ExtraPricingTypeEnum(str, PyEnum):
    PER_DAY = "per_day"
    PER_TRIP = "per_trip"


class Extra(Base, TimestampMixin):
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[ExtraTypeEnum] = mapped_column(SAEnum(ExtraTypeEnum), index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    pricing_type: Mapped[ExtraPricingTypeEnum] = mapped_column(
        SAEnum(ExtraPricingTypeEnum, values_callable=lambda x: [e.value for e in x]),
        default=ExtraPricingTypeEnum.PER_DAY, server_default="per_day"
    )
    max_quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    bookings: Mapped[List["BookingExtra"]] = relationship(back_populates="extra")


class BookingExtra(Base, TimestampMixin):
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    extra_id: Mapped[int] = mapped_column(ForeignKey("extra.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    booking: Mapped["Booking"] = relationship(back_populates="extras")
    extra: Mapped["Extra"] = relationship(back_populates="bookings")
