from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, ForeignKey, Numeric, Date, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .vehicle import Vehicle


class MaintenanceServiceType(Base, TimestampMixin):
    """
    Types of maintenance services (Oil Change, Brake Service, etc.)
    """
    __tablename__ = "maintenance_service_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    average_time_hours: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True, comment="Average time in hours")
    default_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, comment="Default price in GEL")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    services: Mapped[list["MaintenanceService"]] = relationship(
        "MaintenanceService",
        back_populates="service_type",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MaintenanceServiceType(id={self.id}, name='{self.name}')>"


class MaintenanceService(Base, TimestampMixin):
    """
    Individual maintenance service records for vehicles
    """
    __tablename__ = "maintenance_services"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False)
    service_type_id: Mapped[int] = mapped_column(ForeignKey("maintenance_service_types.id", ondelete="RESTRICT"), nullable=False)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, comment="Admin who took vehicle for service")
    pickup_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Pickup datetime")
    dropoff_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Drop-off datetime")
    branch_office: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mileage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Mileage at time of service")
    cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, comment="Actual cost in GEL")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Programmed", server_default="Programmed")
    mechanic_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shop_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    next_service_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    next_service_mileage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="maintenance_services")
    service_type: Mapped["MaintenanceServiceType"] = relationship("MaintenanceServiceType", back_populates="services")
    admin: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<MaintenanceService(id={self.id}, vehicle_id={self.vehicle_id}, service_type_id={self.service_type_id})>"
