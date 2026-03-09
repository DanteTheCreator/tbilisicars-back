from __future__ import annotations

from typing import List, TYPE_CHECKING

from sqlalchemy import String, Table, Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .vehicle import Vehicle
    from .booking import Booking


# Junction table for partner-vehicle many-to-many relationship
partner_vehicle = Table(
    'partner_vehicle',
    Base.metadata,
    Column('partner_id', Integer, ForeignKey('partner.id', ondelete='CASCADE'), primary_key=True),
    Column('vehicle_id', Integer, ForeignKey('vehicle.id', ondelete='CASCADE'), primary_key=True),
)


class Partner(Base, TimestampMixin):
    """Business partners/brokers (e.g., DiscoverCars, VIPCars, etc.)"""
    
    __tablename__ = "partner"
    __table_args__ = (
        UniqueConstraint("name", name="uq_partner_name"),
    )

    name: Mapped[str] = mapped_column(String(150), index=True)
    contact_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    
    # Relations
    vehicles: Mapped[List["Vehicle"]] = relationship(
        "Vehicle",
        secondary=partner_vehicle,
        back_populates="partners"
    )
    documents: Mapped[List["PartnerDocument"]] = relationship(
        "PartnerDocument",
        back_populates="partner",
        cascade="all, delete-orphan"
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="partner",
        foreign_keys="[Booking.partner_id]"
    )

    def __repr__(self):
        return f"<Partner(id={self.id}, name='{self.name}')>"


class PartnerDocument(Base, TimestampMixin):
    """Documents uploaded for partners (contracts, agreements, etc.)"""
    
    __tablename__ = "partner_document"

    partner_id: Mapped[int] = mapped_column(ForeignKey("partner.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    file_path: Mapped[str] = mapped_column(String(500))

    # Relations
    partner: Mapped["Partner"] = relationship("Partner", back_populates="documents")

    def __repr__(self):
        return f"<PartnerDocument(id={self.id}, partner_id={self.partner_id}, title='{self.title}')>"
