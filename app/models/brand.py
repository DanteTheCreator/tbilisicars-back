from __future__ import annotations

from typing import List, TYPE_CHECKING

from sqlalchemy import String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .vehicle_model import VehicleModel


class Brand(Base, TimestampMixin):
    """Vehicle brand/manufacturer (e.g., Toyota, Mercedes-Benz, BMW)"""
    
    __tablename__ = "brand"
    __table_args__ = (
        UniqueConstraint("name", name="uq_brand_name"),
    )

    name: Mapped[str] = mapped_column(String(100), index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Relations
    models: Mapped[List["VehicleModel"]] = relationship("VehicleModel", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"
