from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_password_hash, get_current_super_admin
from app.core.db import get_db
from app.models.admin import Admin

router = APIRouter(prefix="/admin", tags=["Admin Management"])


class AdminResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    admin_role: str
    is_active: bool
    can_manage_vehicles: bool
    can_manage_bookings: bool
    can_manage_users: bool
    can_view_reports: bool
    can_manage_settings: bool
    last_login: Optional[str]
    created_at: str


class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    admin_role: str = "guest_admin"
    can_manage_vehicles: bool = True
    can_manage_bookings: bool = True
    can_manage_users: bool = False
    can_view_reports: bool = True
    can_manage_settings: bool = False


class UpdateAdminRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    admin_role: Optional[str] = None
    is_active: Optional[bool] = None
    can_manage_vehicles: Optional[bool] = None
    can_manage_bookings: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_view_reports: Optional[bool] = None
    can_manage_settings: Optional[bool] = None


def admin_to_response(admin: Admin) -> AdminResponse:
    """Convert Admin model to AdminResponse."""
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        full_name=admin.full_name,
        admin_role=admin.admin_role,
        is_active=admin.is_active,
        can_manage_vehicles=admin.can_manage_vehicles,
        can_manage_bookings=admin.can_manage_bookings,
        can_manage_users=admin.can_manage_users,
        can_view_reports=admin.can_view_reports,
        can_manage_settings=admin.can_manage_settings,
        last_login=admin.last_login.isoformat() if admin.last_login else None,
        created_at=admin.created_at.isoformat()
    )


@router.get("/admins", response_model=List[AdminResponse])
async def list_all_admins(
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Get list of all admins. Only accessible by super admins."""
    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    return [admin_to_response(admin) for admin in admins]


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Get specific admin by ID. Only accessible by super admins."""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    return admin_to_response(admin)


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    request: CreateAdminRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new admin. Only accessible by super admins."""
    
    # Check if username already exists
    existing_username = db.query(Admin).filter(Admin.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Admin).filter(Admin.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Validate admin role
    valid_roles = ["super_admin", "admin", "guest_admin"]
    if request.admin_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid admin role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Create new admin
    new_admin = Admin(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        admin_role=request.admin_role,
        is_active=True,
        can_manage_vehicles=request.can_manage_vehicles,
        can_manage_bookings=request.can_manage_bookings,
        can_manage_users=request.can_manage_users,
        can_view_reports=request.can_view_reports,
        can_manage_settings=request.can_manage_settings
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return admin_to_response(new_admin)


@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    request: UpdateAdminRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Update an admin. Only accessible by super admins."""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Prevent super admin from removing their own super admin role
    if admin.id == current_admin.id and request.admin_role and request.admin_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own super admin privileges"
        )
    
    # Update fields
    if request.username is not None:
        # Check if new username is already taken by another admin
        existing = db.query(Admin).filter(Admin.username == request.username, Admin.id != admin_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        admin.username = request.username
    
    if request.email is not None:
        # Check if new email is already taken by another admin
        existing = db.query(Admin).filter(Admin.email == request.email, Admin.id != admin_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        admin.email = request.email
    
    if request.full_name is not None:
        admin.full_name = request.full_name
    
    if request.password is not None and request.password.strip():
        # Update password only if provided and not empty
        admin.hashed_password = get_password_hash(request.password)
    
    if request.admin_role is not None:
        valid_roles = ["super_admin", "admin", "guest_admin"]
        if request.admin_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid admin role. Must be one of: {', '.join(valid_roles)}"
            )
        admin.admin_role = request.admin_role
    
    if request.is_active is not None:
        # Prevent super admin from deactivating themselves
        if admin.id == current_admin.id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        admin.is_active = request.is_active
    
    if request.can_manage_vehicles is not None:
        admin.can_manage_vehicles = request.can_manage_vehicles
    
    if request.can_manage_bookings is not None:
        admin.can_manage_bookings = request.can_manage_bookings
    
    if request.can_manage_users is not None:
        admin.can_manage_users = request.can_manage_users
    
    if request.can_view_reports is not None:
        admin.can_view_reports = request.can_view_reports
    
    if request.can_manage_settings is not None:
        admin.can_manage_settings = request.can_manage_settings
    
    db.commit()
    db.refresh(admin)
    
    return admin_to_response(admin)


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: int,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Delete an admin. Only accessible by super admins."""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Prevent super admin from deleting themselves
    if admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(admin)
    db.commit()
    
    return {"message": "Admin deleted successfully"}
