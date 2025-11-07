from __future__ import annotations

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Boolean, DateTime, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .task import Task


class AdminRole(str, enum.Enum):
    """Admin user role hierarchy."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    GUEST_ADMIN = "guest_admin"


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"
    
    __table_args__ = (
        UniqueConstraint("email", name="uq_admin_email"),
        UniqueConstraint("username", name="uq_admin_username"),
    )

    username: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    
    # Auth
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Role-based hierarchy
    admin_role: Mapped[str] = mapped_column(
        String(20),
        default="guest_admin",
        nullable=False
    )
    
    # Deprecated: Kept for backward compatibility during migration
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Session management
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Permissions - granular control for each admin section
    can_manage_vehicles: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_bookings: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_settings: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_rates: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_extras: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_promotions: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_locations: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_reviews: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_damages: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_tasks: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_calendar: Mapped[bool] = mapped_column(Boolean, default=True)

    # Task relationships
    created_tasks: Mapped[list["Task"]] = relationship("Task", foreign_keys="Task.created_by_id", back_populates="created_by")
    assigned_tasks: Mapped[list["Task"]] = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assigned_to")

    def __repr__(self) -> str:
        return f"<Admin {self.username} ({self.admin_role})>"
    
    @property
    def is_super_admin_role(self) -> bool:
        """Check if admin has super admin role."""
        return self.admin_role == "super_admin"
    
    @property
    def is_admin_role(self) -> bool:
        """Check if admin has admin role or higher."""
        return self.admin_role in ("super_admin", "admin")
    
    @property
    def is_guest_admin_role(self) -> bool:
        """Check if admin has guest admin role."""
        return self.admin_role == "guest_admin"
