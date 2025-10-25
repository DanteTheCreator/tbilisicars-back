from __future__ import annotations

from typing import List, Optional
from datetime import date

from sqlalchemy import String, Integer, ForeignKey, Numeric, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Rate(Base, TimestampMixin):
    """
    Rate strategy - defines pricing rules for vehicle groups
    Similar to rental software rate strategies with parent/child relationships
    """
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Parent Rate for incremental pricing
    parent_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("rate.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    
    # Increment over parent (can be positive or negative percentage/amount)
    increment_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "percentage" or "fixed"
    increment_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Date Range
    valid_from: Mapped[date] = mapped_column(Date, index=True)
    valid_until: Mapped[date] = mapped_column(Date, index=True)
    
    # Rental Duration Constraints
    min_days: Mapped[int] = mapped_column(Integer, default=2)
    max_days: Mapped[int | None] = mapped_column(Integer, nullable=True, default=300)
    
    # Mileage Settings
    unlimited_km: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Who can edit
    editable_by: Mapped[str] = mapped_column(String(50), default="all")  # "all", "admin", "manager"
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Price Agreement Modifiers (e.g., "Website - 10%")
    price_modifier_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_modifier_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "percentage" or "fixed"
    price_modifier_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_modifier_applies_to_agreement_only: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relations
    parent_rate: Mapped[Optional["Rate"]] = relationship(
        "Rate",
        remote_side="Rate.id",
        back_populates="child_rates"
    )
    child_rates: Mapped[List["Rate"]] = relationship(
        "Rate",
        back_populates="parent_rate",
        cascade="all, delete-orphan"
    )
    
    # Rate tiers (day ranges with prices per vehicle group)
    rate_tiers: Mapped[List["RateTier"]] = relationship(
        back_populates="rate",
        cascade="all, delete-orphan",
        order_by="RateTier.from_days"
    )
    
    # Day ranges (0-3, 4-7, 8-13, etc.)
    day_ranges: Mapped[List["RateDayRange"]] = relationship(
        back_populates="rate",
        cascade="all, delete-orphan",
        order_by="RateDayRange.from_days"
    )
    
    # Hour ranges (if hourly pricing enabled)
    hour_ranges: Mapped[List["RateHourRange"]] = relationship(
        back_populates="rate",
        cascade="all, delete-orphan"
    )
    
    # KM ranges (if not unlimited)
    km_ranges: Mapped[List["RateKmRange"]] = relationship(
        back_populates="rate",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Rate(id={self.id}, name='{self.name}')>"


class RateTier(Base, TimestampMixin):
    """
    Price tier for a rate - defines pricing for a vehicle group within day ranges
    Example: Economy cars cost €36.00 for 0-3 days, €30.38 for 4-7 days, etc.
    """
    
    rate_id: Mapped[int] = mapped_column(ForeignKey("rate.id", ondelete="CASCADE"), index=True)
    vehicle_group_id: Mapped[int] = mapped_column(ForeignKey("vehiclegroup.id", ondelete="CASCADE"), index=True)
    
    # Day range for this tier
    from_days: Mapped[int] = mapped_column(Integer, default=0)
    to_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL means unlimited
    
    # Price for this tier
    price_per_day: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    
    # Relations
    rate: Mapped["Rate"] = relationship(back_populates="rate_tiers")
    vehicle_group: Mapped["VehicleGroup"] = relationship()
    
    def __repr__(self) -> str:
        return f"<RateTier(rate={self.rate_id}, group={self.vehicle_group_id}, {self.from_days}-{self.to_days} days, €{self.price_per_day})>"


class RateDayRange(Base, TimestampMixin):
    """
    Day ranges configuration for a rate (e.g., 0-3, 4-7, 8-13, 14-30, 31-364)
    Defines the buckets for pricing tiers
    """
    
    rate_id: Mapped[int] = mapped_column(ForeignKey("rate.id", ondelete="CASCADE"), index=True)
    
    from_days: Mapped[int] = mapped_column(Integer)
    to_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL means unlimited
    
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "0 to 3 Days", "31 to 364 Days"
    
    rate: Mapped["Rate"] = relationship(back_populates="day_ranges")
    
    def __repr__(self) -> str:
        return f"<RateDayRange({self.from_days}-{self.to_days} days)>"


class RateHourRange(Base, TimestampMixin):
    """
    Hour ranges for hourly pricing (if enabled)
    """
    
    rate_id: Mapped[int] = mapped_column(ForeignKey("rate.id", ondelete="CASCADE"), index=True)
    
    from_hours: Mapped[int] = mapped_column(Integer)
    to_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    rate: Mapped["Rate"] = relationship(back_populates="hour_ranges")


class RateKmRange(Base, TimestampMixin):
    """
    KM/mileage ranges for rates (if not unlimited)
    """
    
    rate_id: Mapped[int] = mapped_column(ForeignKey("rate.id", ondelete="CASCADE"), index=True)
    
    from_km: Mapped[int] = mapped_column(Integer, default=0)
    to_km: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL means unlimited
    
    label: Mapped[str] = mapped_column(String(50))  # e.g., "Unlimited", "0-1000 km"
    
    rate: Mapped["Rate"] = relationship(back_populates="km_ranges")
