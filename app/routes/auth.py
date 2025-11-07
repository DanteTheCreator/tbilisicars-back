from __future__ import annotations

from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer

from app.core.auth import (
    authenticate_admin, 
    create_access_token, 
    get_current_admin,
    get_password_hash,
    security,
    verify_token as verify_jwt_token
)
from app.core.config import get_settings
from app.core.db import get_db
from app.models.admin import Admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    admin: Dict[str, Any]


class AdminInfo(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    admin_role: str
    is_active: bool
    is_super_admin: bool  # Kept for backward compatibility
    can_manage_vehicles: bool
    can_manage_bookings: bool
    can_manage_users: bool
    can_view_reports: bool
    can_manage_settings: bool
    can_manage_rates: bool
    can_manage_extras: bool
    can_manage_promotions: bool
    can_manage_locations: bool
    can_view_reviews: bool
    can_manage_damages: bool
    can_manage_tasks: bool
    can_view_calendar: bool
    last_login: str | None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Admin login endpoint."""
    admin = authenticate_admin(db, request.username, request.password)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(admin.id)},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        admin={
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "full_name": admin.full_name,
            "admin_role": admin.admin_role,
            "is_active": admin.is_active,
            "is_super_admin": admin.is_super_admin,
            "can_manage_vehicles": admin.can_manage_vehicles,
            "can_manage_bookings": admin.can_manage_bookings,
            "can_manage_users": admin.can_manage_users,
            "can_view_reports": admin.can_view_reports,
            "can_manage_settings": admin.can_manage_settings,
            "can_manage_rates": admin.can_manage_rates,
            "can_manage_extras": admin.can_manage_extras,
            "can_manage_promotions": admin.can_manage_promotions,
            "can_manage_locations": admin.can_manage_locations,
            "can_view_reviews": admin.can_view_reviews,
            "can_manage_damages": admin.can_manage_damages,
            "can_manage_tasks": admin.can_manage_tasks,
            "can_view_calendar": admin.can_view_calendar,
            "last_login": admin.last_login.isoformat() if admin.last_login else None
        }
    )


@router.get("/me", response_model=AdminInfo)
async def get_current_user_info(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get current admin information."""
    return AdminInfo(
        id=current_admin.id,
        username=current_admin.username,
        email=current_admin.email,
        full_name=current_admin.full_name,
        admin_role=current_admin.admin_role,
        is_active=current_admin.is_active,
        is_super_admin=current_admin.is_super_admin,
        can_manage_vehicles=current_admin.can_manage_vehicles,
        can_manage_bookings=current_admin.can_manage_bookings,
        can_manage_users=current_admin.can_manage_users,
        can_view_reports=current_admin.can_view_reports,
        can_manage_settings=current_admin.can_manage_settings,
        can_manage_rates=current_admin.can_manage_rates,
        can_manage_extras=current_admin.can_manage_extras,
        can_manage_promotions=current_admin.can_manage_promotions,
        can_manage_locations=current_admin.can_manage_locations,
        can_view_reviews=current_admin.can_view_reviews,
        can_manage_damages=current_admin.can_manage_damages,
        can_manage_tasks=current_admin.can_manage_tasks,
        can_view_calendar=current_admin.can_view_calendar,
        last_login=current_admin.last_login.isoformat() if current_admin.last_login else None
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Admin logout endpoint."""
    # For now, just return success. In production, you might want to:
    # - Add token to blacklist
    # - Clear any server-side sessions
    return {"message": "Successfully logged out"}


@router.post("/verify")
async def verify_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Verify if current token is valid."""
    try:
        payload = verify_jwt_token(credentials.credentials)
        if payload is None:
            return {"valid": False, "error": "Invalid token"}
        
        admin_id_str = payload.get("sub")
        if admin_id_str is None:
            return {"valid": False, "error": "No sub in token"}
        
        # Convert string to integer
        admin_id = int(admin_id_str)
        
        # Try to find admin
        admin = db.query(Admin).filter(Admin.id == int(admin_id)).first()
        if not admin:
            return {"valid": False, "error": f"Admin not found with id {admin_id}"}
            
        return {
            "valid": True,
            "admin_id": admin.id,
            "username": admin.username,
            "debug": {
                "token_sub": admin_id_str,
                "parsed_id": admin_id,
                "admin_found": True
            }
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change admin password."""
    from app.core.auth import verify_password
    
    # Verify current password
    if not verify_password(request.current_password, current_admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password (you can add more validation here)
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    # Update password
    current_admin.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
