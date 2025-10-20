from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy import String, Boolean, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
    )

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Auth (optional - only for admin users)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Driver info
    driver_license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    driver_license_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    driver_license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relations
    bookings: Mapped[List["Booking"]] = relationship(back_populates="user")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user")
    reviews: Mapped[List["Review"]] = relationship(back_populates="user")
