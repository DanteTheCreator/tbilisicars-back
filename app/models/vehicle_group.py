from __future__ import annotations

from typing import List, Optional

from sqlalchemy import String, Text, Integer, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class VehicleGroup(Base, TimestampMixin):
    """
    Vehicle Group model - represents a category/group of similar vehicles.
    Individual vehicles are assigned to these groups.
    """
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Vehicle Specifications (common to group)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "Economy", "SUV", "Luxury"
    seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "Automatic", "Manual"
    fuel_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "Gasoline", "Diesel", "Electric"
    
    # Pricing (base prices for the group)
    base_price_per_day: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    base_price_per_week: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    base_price_per_month: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Features (stored as comma-separated or JSON in production you might use JSON type)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g., "GPS,Bluetooth,Air Conditioning,USB Port"
    
    # Display settings
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Availability settings
    min_rental_days: Mapped[int] = mapped_column(Integer, default=1)
    max_rental_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Relations
    vehicles: Mapped[List["Vehicle"]] = relationship(
        back_populates="vehicle_group",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    def __repr__(self) -> str:
        return f"<VehicleGroup(id={self.id}, name='{self.name}', category='{self.category}')>"
