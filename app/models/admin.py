from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


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
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Session management
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Permissions - can be extended later
    can_manage_vehicles: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_bookings: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_settings: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Admin {self.username}>"
