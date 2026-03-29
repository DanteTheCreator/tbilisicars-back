from __future__ import annotations

from sqlalchemy import String, Numeric, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class CompanySettings(Base, TimestampMixin):
    """
    Singleton-style table for company/site settings.
    There should be exactly one row (id=1).
    """
    __tablename__ = "company_settings"

    company_name: Mapped[str] = mapped_column(String(200), default="TbilisiCars")
    company_legal_name: Mapped[str] = mapped_column(String(200), default="TbilisiCars LLC")
    company_email: Mapped[str] = mapped_column(String(255), default="reservations@tbilisicars.com")
    company_phone: Mapped[str] = mapped_column(String(50), default="+995 591 00 26 30")
    company_address: Mapped[str] = mapped_column(String(500), default="Tbilisi, Georgia")
    company_website: Mapped[str] = mapped_column(String(255), default="https://tbilisicars.live")

    default_currency: Mapped[str] = mapped_column(String(3), default="USD")
    default_timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tbilisi")
