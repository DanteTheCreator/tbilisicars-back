from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.core.auth import get_current_admin, require_permission
from app.core.db import get_db
from app.models.admin import Admin

router = APIRouter()

# Default settings structure
DEFAULT_SETTINGS = {
    "general": {
        "company_name": "TbilisiCars",
        "company_email": "admin@tbilisicars.com",
        "company_phone": "+995 555 123 456",
        "company_address": "Tbilisi, Georgia",
        "currency": "USD",
        "timezone": "Asia/Tbilisi",
        "language": "en"
    },
    "booking": {
        "advance_booking_days": 365,
        "min_booking_duration": 1,
        "max_booking_duration": 30,
        "cancellation_policy": "24_hours",
        "require_payment_upfront": True,
        "auto_confirm_bookings": False
    },
    "pricing": {
        "tax_rate": 0.18,
        "late_return_fee": 50.0,
        "damage_deposit": 500.0,
        "cleaning_fee": 25.0,
        "delivery_fee": 30.0,
        "insurance_daily_rate": 15.0
    },
    "notifications": {
        "email_notifications": True,
        "sms_notifications": False,
        "booking_confirmations": True,
        "reminder_emails": True,
        "marketing_emails": False,
        "webhook_url": ""
    },
    "maintenance": {
        "service_interval_km": 10000,
        "oil_change_interval": 6,
        "inspection_interval": 12,
        "auto_schedule_maintenance": True,
        "maintenance_buffer_days": 3
    },
    "vehicles": {
        "default_fuel_level": 100,
        "min_fuel_level": 25,
        "require_inspection_photos": True,
        "auto_assign_vehicles": False,
        "vehicle_age_limit": 10
    }
}

@router.get("/admin/settings")
async def get_all_settings(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get all system settings
    """
    # In a real implementation, these would be stored in a database
    # For now, return default settings
    return DEFAULT_SETTINGS

@router.get("/admin/settings/{category}")
async def get_settings_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get settings for a specific category
    """
    if category not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Settings category '{category}' not found")
    
    return {category: DEFAULT_SETTINGS[category]}

@router.put("/admin/settings")
async def update_all_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("can_manage_settings"))
) -> Dict[str, Any]:
    """
    Update all system settings
    """
    # In a real implementation, these would be saved to database
    # For now, just return the updated settings
    return {
        "message": "Settings updated successfully",
        "settings": settings
    }

@router.patch("/admin/settings")
async def patch_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("can_manage_settings"))
) -> Dict[str, Any]:
    """
    Partially update system settings
    """
    # In a real implementation, these would be merged with existing settings
    return {
        "message": "Settings updated successfully",
        "updated_fields": list(settings.keys())
    }

@router.put("/admin/settings/{category}")
async def update_settings_category(
    category: str,
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("can_manage_settings"))
) -> Dict[str, Any]:
    """
    Update settings for a specific category
    """
    if category not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Settings category '{category}' not found")
    
    return {
        "message": f"Settings for '{category}' updated successfully",
        "category": category,
        "settings": settings
    }

@router.patch("/admin/settings/{category}")
async def patch_settings_category(
    category: str,
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_permission("can_manage_settings"))
) -> Dict[str, Any]:
    """
    Partially update settings for a specific category
    """
    if category not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Settings category '{category}' not found")
    
    return {
        "message": f"Settings for '{category}' updated successfully",
        "category": category,
        "updated_fields": list(settings.keys())
    }
