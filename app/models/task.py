from __future__ import annotations

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    """Task status options."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    """Task priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Task(Base, TimestampMixin):
    """Task model for admin task management."""
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dates
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status and Priority
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        default=TaskStatus.PENDING,
        nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=20),
        default=TaskPriority.MEDIUM,
        nullable=False
    )
    
    # Foreign Keys
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Related entities (optional)
    related_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehicle.id"), nullable=True)
    related_booking_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("booking.id"), nullable=True)
    
    # Relationships
    created_by: Mapped["Admin"] = relationship("Admin", foreign_keys=[created_by_id], back_populates="created_tasks")
    assigned_to: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[assigned_to_id], back_populates="assigned_tasks")
    related_vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", foreign_keys=[related_vehicle_id], viewonly=True)
    related_booking: Mapped[Optional["Booking"]] = relationship("Booking", foreign_keys=[related_booking_id], viewonly=True)

    def __repr__(self) -> str:
        return f"<Task {self.name} ({self.status.value})>"
