from __future__ import annotations

from typing import List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Boolean, UniqueConstraint, Text, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .brand import Brand
    from .vehicle import Vehicle
    from .vehicle_photo import VehiclePhoto


class VehicleModel(Base, TimestampMixin):
    """Vehicle model (e.g., Camry, CLK, X5) - belongs to a Brand"""
    
    __tablename__ = "vehicle_model"
    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_brand_model_name"),
    )

    brand_id: Mapped[int] = mapped_column(ForeignKey("brand.id", ondelete="CASCADE"), index=True)
    
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # External system availability
    available_for_external_systems: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Category (e.g., Economy, Standard, SUV, etc.)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Specifications
    passengers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    large_suitcases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    small_suitcases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Fuel information
    fuel_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Gasoline, Diesel, Electric, Hybrid
    fuel_tank_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Fuel tank size in liters
    
    # Deposit
    deposit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True, default=0)
    
    # Relations
    brand: Mapped["Brand"] = relationship("Brand", back_populates="models")
    vehicles: Mapped[List["Vehicle"]] = relationship("Vehicle", back_populates="vehicle_model", cascade="all, delete-orphan")
    photos: Mapped[List["VehiclePhoto"]] = relationship("VehiclePhoto", back_populates="vehicle_model", cascade="all, delete-orphan", order_by="VehiclePhoto.display_order")

    def __repr__(self):
        return f"<VehicleModel(id={self.id}, brand_id={self.brand_id}, name='{self.name}')>"
