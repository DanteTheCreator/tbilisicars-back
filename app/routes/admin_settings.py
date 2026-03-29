from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.core.auth import get_current_admin, require_permission
from app.core.db import get_db
from app.models.admin import Admin
from app.models.company_settings import CompanySettings

router = APIRouter()


def get_company_settings(db: Session) -> CompanySettings:
    """Fetch company settings row from DB, or create it with defaults if missing."""
    settings = db.query(CompanySettings).filter(CompanySettings.id == 1).first()
    if not settings:
        settings = CompanySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    company_legal_name: Optional[str] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    company_website: Optional[str] = None
    default_currency: Optional[str] = None
    default_timezone: Optional[str] = None


@router.get("/admin/settings")
async def get_all_settings(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Get all system settings (company info from DB)."""
    cs = get_company_settings(db)
    return {
        "general": {
            "company_name": cs.company_name,
            "company_legal_name": cs.company_legal_name,
            "company_email": cs.company_email,
            "company_phone": cs.company_phone,
            "company_address": cs.company_address,
            "company_website": cs.company_website,
            "currency": cs.default_currency,
            "timezone": cs.default_timezone,
        },
    }


@router.get("/admin/settings/general")
async def get_general_settings(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """Get general/company settings."""
    cs = get_company_settings(db)
    return {
        "general": {
            "company_name": cs.company_name,
            "company_legal_name": cs.company_legal_name,
            "company_email": cs.company_email,
            "company_phone": cs.company_phone,
            "company_address": cs.company_address,
            "company_website": cs.company_website,
            "currency": cs.default_currency,
            "timezone": cs.default_timezone,
        }
    }


@router.patch("/admin/settings")
async def patch_settings(
    payload: CompanySettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("can_manage_settings"))
) -> Dict[str, Any]:
    """Update company settings (partial update)."""
    cs = get_company_settings(db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cs, key, value)
    db.commit()
    db.refresh(cs)
    return {
        "message": "Settings updated successfully",
        "settings": {
            "company_name": cs.company_name,
            "company_legal_name": cs.company_legal_name,
            "company_email": cs.company_email,
            "company_phone": cs.company_phone,
            "company_address": cs.company_address,
            "company_website": cs.company_website,
            "currency": cs.default_currency,
            "timezone": cs.default_timezone,
        }
    }
