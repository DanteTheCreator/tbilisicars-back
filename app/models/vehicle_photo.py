from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .vehicle import Vehicle
    from .vehicle_model import VehicleModel


class VehiclePhoto(Base, TimestampMixin):
    """Model for storing vehicle photo metadata and MinIO object references
    
    Photos can be attached to either:
    - A specific vehicle (vehicle_id)
    - A vehicle model (vehicle_model_id) - shared by all vehicles of that model
    
    When fetching vehicle photos, model photos are included if the vehicle has no specific photos.
    """
    
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=True, index=True)
    vehicle_model_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_model.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # MinIO object information
    object_name: Mapped[str] = mapped_column(String(500), unique=True, index=True)  # MinIO object path
    original_filename: Mapped[str] = mapped_column(String(255))  # Original uploaded filename
    file_size: Mapped[int] = mapped_column(Integer)  # File size in bytes
    content_type: Mapped[str] = mapped_column(String(100))  # MIME type (image/jpeg, etc.)
    
    # Photo metadata
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # Main photo for vehicle/model
    display_order: Mapped[int] = mapped_column(Integer, default=0)  # Order for gallery display
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Alt text for accessibility
    
    # Relations
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", back_populates="photos")
    vehicle_model: Mapped["VehicleModel | None"] = relationship("VehicleModel", back_populates="photos")
