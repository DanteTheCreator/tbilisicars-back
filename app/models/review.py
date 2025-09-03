from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Enum, Integer, ForeignKey, SmallInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .vehicle import Vehicle


class Review(Base, TimestampMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), index=True)

    rating: Mapped[int] = mapped_column(SmallInteger)  # 1-5
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="reviews")
    vehicle: Mapped[Vehicle] = relationship()
