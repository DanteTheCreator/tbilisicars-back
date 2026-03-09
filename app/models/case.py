from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CasePriority(str, enum.Enum):
    """Case priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CaseStatus(str, enum.Enum):
    """Case status options."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


# Association table for case assignments
case_assignments = Table(
    "case_assignments",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("admin_id", Integer, ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow, nullable=False)
)


class Case(Base, TimestampMixin):
    """Case model for tracking support cases and issues."""
    __tablename__ = "cases"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status and Priority
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, native_enum=False, length=20),
        default=CaseStatus.OPEN,
        nullable=False
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority, native_enum=False, length=20),
        default=CasePriority.MEDIUM,
        nullable=False
    )
    
    # Foreign Keys
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    
    # Optional related entities
    related_booking_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("booking.id"), nullable=True)
    related_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id"), nullable=True)
    
    # Relationships
    created_by: Mapped["Admin"] = relationship("Admin", foreign_keys=[created_by_id], back_populates="created_cases")
    assigned_admins: Mapped[List["Admin"]] = relationship(
        "Admin",
        secondary=case_assignments,
        back_populates="assigned_cases"
    )
    comments: Mapped[List["CaseComment"]] = relationship("CaseComment", back_populates="case", cascade="all, delete-orphan")
    attachments: Mapped[List["CaseAttachment"]] = relationship("CaseAttachment", back_populates="case", cascade="all, delete-orphan")
    
    related_booking: Mapped[Optional["Booking"]] = relationship("Booking", foreign_keys=[related_booking_id])
    related_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[related_user_id])


class CaseComment(Base, TimestampMixin):
    """Comments on cases."""
    __tablename__ = "case_comments"

    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="comments")
    admin: Mapped["Admin"] = relationship("Admin", back_populates="case_comments")
    attachments: Mapped[List["CaseAttachment"]] = relationship(
        "CaseAttachment",
        back_populates="comment",
        cascade="all, delete-orphan"
    )


class CaseAttachment(Base, TimestampMixin):
    """File attachments for cases and comments."""
    __tablename__ = "case_attachments"

    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("case_comments.id", ondelete="CASCADE"), nullable=True)
    admin_id: Mapped[int] = mapped_column(Integer, ForeignKey("admins.id"), nullable=False)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="attachments")
    comment: Mapped[Optional["CaseComment"]] = relationship("CaseComment", back_populates="attachments")
    admin: Mapped["Admin"] = relationship("Admin", back_populates="case_attachments")
