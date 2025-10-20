from __future__ import annotations

from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class BookingPhoto(Base, TimestampMixin):
    """Model for storing booking-related photo metadata and MinIO object references"""

    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), index=True)

    # MinIO object information
    object_name: Mapped[str] = mapped_column(String(500), unique=True, index=True)  # MinIO object path
    original_filename: Mapped[str] = mapped_column(String(255))  # Original uploaded filename
    file_size: Mapped[int] = mapped_column(Integer)  # File size in bytes
    content_type: Mapped[str] = mapped_column(String(100))  # MIME type (image/jpeg, etc.)

    # Photo metadata
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relations
    booking: Mapped["Booking"] = relationship(back_populates="photos")
