from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer, Boolean, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

# Association table for task assignees (many-to-many)
task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("admin_id", Integer, ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, server_default=func.now(), nullable=False)
)

# Association table for task group assignees (many-to-many)
task_group_assignees = Table(
    "task_group_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("admin_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, server_default=func.now(), nullable=False)
)


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
    
    # Privacy
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    
    # Foreign Keys
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Related entities (optional)
    related_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehicle.id"), nullable=True)
    related_booking_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("booking.id"), nullable=True)
    
    # Relationships
    created_by: Mapped["Admin"] = relationship("Admin", foreign_keys=[created_by_id], back_populates="created_tasks")
    assigned_to: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[assigned_to_id], back_populates="assigned_tasks")
    assignees: Mapped[List["Admin"]] = relationship(
        "Admin",
        secondary=task_assignees,
        back_populates="assigned_task_list"
    )
    assigned_groups: Mapped[List["AdminGroup"]] = relationship(
        "AdminGroup",
        secondary=task_group_assignees,
        backref="assigned_tasks"
    )
    comments: Mapped[List["TaskComment"]] = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    related_vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", foreign_keys=[related_vehicle_id], viewonly=True)
    related_booking: Mapped[Optional["Booking"]] = relationship("Booking", foreign_keys=[related_booking_id], viewonly=True)

    def __repr__(self) -> str:
        return f"<Task {self.name} ({self.status.value})>"


class TaskComment(Base, TimestampMixin):
    """Comments on tasks."""
    __tablename__ = "task_comments"

    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    admin: Mapped["Admin"] = relationship("Admin")
