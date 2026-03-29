from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, Text, Table, Column, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .admin import Admin

# Many-to-many junction table for admin-group membership
admin_group_members = Table(
    "admin_group_members",
    Base.metadata,
    Column("admin_id", ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("admin_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime, server_default=func.now()),
)


class AdminGroup(Base, TimestampMixin):
    __tablename__ = "admin_groups"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Group-level permissions
    can_manage_vehicles: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_bookings: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_settings: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_rates: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_extras: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_promotions: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_locations: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_reviews: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_damages: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_calendar: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_cases: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    members: Mapped[list["Admin"]] = relationship(
        "Admin", secondary=admin_group_members, back_populates="groups"
    )

    def __repr__(self) -> str:
        return f"<AdminGroup {self.name}>"
