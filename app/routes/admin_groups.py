from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_super_admin, get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.admin_group import AdminGroup, admin_group_members

router = APIRouter(prefix="/admin/groups", tags=["Admin Groups"])


# --- Pydantic schemas ---

class GroupMemberResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    admin_role: str


class AdminGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
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
    can_manage_cases: bool
    members: List[GroupMemberResponse]
    created_at: str


class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    can_manage_vehicles: bool = False
    can_manage_bookings: bool = False
    can_manage_users: bool = False
    can_view_reports: bool = False
    can_manage_settings: bool = False
    can_manage_rates: bool = False
    can_manage_extras: bool = False
    can_manage_promotions: bool = False
    can_manage_locations: bool = False
    can_view_reviews: bool = False
    can_manage_damages: bool = False
    can_manage_tasks: bool = False
    can_view_calendar: bool = False
    can_manage_cases: bool = False
    member_ids: List[int] = []


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    can_manage_vehicles: Optional[bool] = None
    can_manage_bookings: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_view_reports: Optional[bool] = None
    can_manage_settings: Optional[bool] = None
    can_manage_rates: Optional[bool] = None
    can_manage_extras: Optional[bool] = None
    can_manage_promotions: Optional[bool] = None
    can_manage_locations: Optional[bool] = None
    can_view_reviews: Optional[bool] = None
    can_manage_damages: Optional[bool] = None
    can_manage_tasks: Optional[bool] = None
    can_view_calendar: Optional[bool] = None
    can_manage_cases: Optional[bool] = None
    member_ids: Optional[List[int]] = None


class UpdateGroupMembersRequest(BaseModel):
    member_ids: List[int]


# --- Helpers ---

PERMISSION_FIELDS = [
    "can_manage_vehicles", "can_manage_bookings", "can_manage_users",
    "can_view_reports", "can_manage_settings", "can_manage_rates",
    "can_manage_extras", "can_manage_promotions", "can_manage_locations",
    "can_view_reviews", "can_manage_damages", "can_manage_tasks",
    "can_view_calendar", "can_manage_cases",
]


def group_to_response(group: AdminGroup) -> AdminGroupResponse:
    return AdminGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        can_manage_vehicles=group.can_manage_vehicles,
        can_manage_bookings=group.can_manage_bookings,
        can_manage_users=group.can_manage_users,
        can_view_reports=group.can_view_reports,
        can_manage_settings=group.can_manage_settings,
        can_manage_rates=group.can_manage_rates,
        can_manage_extras=group.can_manage_extras,
        can_manage_promotions=group.can_manage_promotions,
        can_manage_locations=group.can_manage_locations,
        can_view_reviews=group.can_view_reviews,
        can_manage_damages=group.can_manage_damages,
        can_manage_tasks=group.can_manage_tasks,
        can_view_calendar=group.can_view_calendar,
        can_manage_cases=group.can_manage_cases,
        members=[
            GroupMemberResponse(
                id=m.id, username=m.username, full_name=m.full_name,
                email=m.email, admin_role=m.admin_role
            ) for m in group.members
        ],
        created_at=group.created_at.isoformat(),
    )


# --- Endpoints ---

@router.get("", response_model=List[AdminGroupResponse])
async def list_groups(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all admin groups. Accessible by any admin."""
    groups = (
        db.query(AdminGroup)
        .options(joinedload(AdminGroup.members))
        .order_by(AdminGroup.name)
        .all()
    )
    # Deduplicate due to joinedload
    seen = set()
    unique = []
    for g in groups:
        if g.id not in seen:
            seen.add(g.id)
            unique.append(g)
    return [group_to_response(g) for g in unique]


@router.get("/{group_id}", response_model=AdminGroupResponse)
async def get_group(
    group_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a specific admin group."""
    group = (
        db.query(AdminGroup)
        .options(joinedload(AdminGroup.members))
        .filter(AdminGroup.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group_to_response(group)


@router.post("", response_model=AdminGroupResponse)
async def create_group(
    request: CreateGroupRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Create a new admin group. Super admin only."""
    existing = db.query(AdminGroup).filter(AdminGroup.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")

    group = AdminGroup(
        name=request.name,
        description=request.description,
    )
    for field in PERMISSION_FIELDS:
        setattr(group, field, getattr(request, field))

    # Add members
    if request.member_ids:
        members = db.query(Admin).filter(Admin.id.in_(request.member_ids)).all()
        group.members = members

    db.add(group)
    db.commit()
    db.refresh(group)
    return group_to_response(group)


@router.put("/{group_id}", response_model=AdminGroupResponse)
async def update_group(
    group_id: int,
    request: UpdateGroupRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Update an admin group. Super admin only."""
    group = (
        db.query(AdminGroup)
        .options(joinedload(AdminGroup.members))
        .filter(AdminGroup.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if request.name is not None:
        existing = (
            db.query(AdminGroup)
            .filter(AdminGroup.name == request.name, AdminGroup.id != group_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Group name already exists")
        group.name = request.name

    if request.description is not None:
        group.description = request.description

    for field in PERMISSION_FIELDS:
        val = getattr(request, field, None)
        if val is not None:
            setattr(group, field, val)

    if request.member_ids is not None:
        members = db.query(Admin).filter(Admin.id.in_(request.member_ids)).all()
        group.members = members

    db.commit()
    db.refresh(group)
    return group_to_response(group)


@router.put("/{group_id}/members", response_model=AdminGroupResponse)
async def update_group_members(
    group_id: int,
    request: UpdateGroupMembersRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Update group members. Super admin only."""
    group = (
        db.query(AdminGroup)
        .options(joinedload(AdminGroup.members))
        .filter(AdminGroup.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = db.query(Admin).filter(Admin.id.in_(request.member_ids)).all()
    group.members = members

    db.commit()
    db.refresh(group)
    return group_to_response(group)


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Delete an admin group. Super admin only."""
    group = db.query(AdminGroup).filter(AdminGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(group)
    db.commit()
    return {"message": "Group deleted successfully"}
