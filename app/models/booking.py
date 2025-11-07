from __future__ import annotations

from datetime import datetime, date
from typing import List

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
    AUTHORIZED = "AUTHORIZED"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Booking(Base, TimestampMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"), index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle.id", ondelete="SET NULL"), index=True, nullable=True)
    vehicle_group_id: Mapped[int | None] = mapped_column(ForeignKey("vehiclegroup.id", ondelete="SET NULL"), index=True, nullable=True)

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
    contact_first_name: Mapped[str] = mapped_column(String(100))
    contact_last_name: Mapped[str] = mapped_column(String(100))
    contact_email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Broker information for bookings from partners (Discover Cars, VIPCars, etc.)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Amounts already present: total_amount and currency

    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relations
    user: Mapped["User"] = relationship(back_populates="bookings")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="bookings")
    vehicle_group: Mapped["VehicleGroup"] = relationship("VehicleGroup", foreign_keys=[vehicle_group_id])
    
    rate: Mapped["Rate"] = relationship("Rate", foreign_keys=[rate_id])
    rate_tier: Mapped["RateTier"] = relationship("RateTier", foreign_keys=[rate_tier_id])

    pickup_location: Mapped["Location"] = relationship(back_populates="pickup_bookings", foreign_keys=[pickup_location_id])
    dropoff_location: Mapped["Location"] = relationship(back_populates="dropoff_bookings", foreign_keys=[dropoff_location_id])

    extras: Mapped[List["BookingExtra"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    damages: Mapped[List["DamageReport"]] = relationship(back_populates="booking")
    photos: Mapped[List["BookingPhoto"]] = relationship(back_populates="booking", cascade="all, delete-orphan")


class ExtraTypeEnum(str, PyEnum):
    GPS = "gps"
    CHILD_SEAT = "child_seat"
    EXTRA_DRIVER = "extra_driver"
    ROOF_RACK = "roof_rack"
    WIFI = "wifi"
    SNOW_CHAINS = "snow_chains"


class Extra(Base, TimestampMixin):
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[ExtraTypeEnum] = mapped_column(SAEnum(ExtraTypeEnum), index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    max_quantity: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    bookings: Mapped[List["BookingExtra"]] = relationship(back_populates="extra")


class BookingExtra(Base, TimestampMixin):
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)
    extra_id: Mapped[int] = mapped_column(ForeignKey("extra.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    booking: Mapped["Booking"] = relationship(back_populates="extras")
    extra: Mapped["Extra"] = relationship(back_populates="bookings")
