from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models.vehicle_group import VehicleGroup
from app.models.vehicle import Vehicle
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/vehicle-groups", tags=["vehicle-groups"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_vehicle_groups(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False)
):
    """List all vehicle groups with optional filtering"""
    query = db.query(VehicleGroup)
    
    if active_only:
        query = query.filter(VehicleGroup.active == True)
    
    query = query.order_by(VehicleGroup.display_order, VehicleGroup.name)
    items = query.offset(skip).limit(limit).all()
    
    return [to_dict(i) for i in items]


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_vehicle_group(item_id: int, db: Session = Depends(get_db)):
    """Get a specific vehicle group by ID"""
    obj = db.get(VehicleGroup, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle group not found"
        )
    return to_dict(obj)


@router.get("/{item_id}/vehicles", response_model=List[Dict[str, Any]])
def get_vehicle_group_vehicles(item_id: int, db: Session = Depends(get_db)):
    """Get all vehicles in a specific vehicle group"""
    group = db.get(VehicleGroup, item_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle group not found"
        )
    
    vehicles = db.query(Vehicle).filter(Vehicle.vehicle_group_id == item_id).all()
    return [to_dict(v) for v in vehicles]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_vehicle_group(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new vehicle group"""
    obj = VehicleGroup()
    apply_updates(obj, payload)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e.orig) if getattr(e, "orig", None) else str(e)
        )
    db.refresh(obj)
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_vehicle_group(
    item_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a vehicle group"""
    obj = db.get(VehicleGroup, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle group not found"
        )
    apply_updates(obj, payload)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e.orig) if getattr(e, "orig", None) else str(e)
        )
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_group(item_id: int, db: Session = Depends(get_db)):
    """Delete a vehicle group (will set vehicles' vehicle_group_id to NULL)"""
    obj = db.get(VehicleGroup, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle group not found"
        )
    db.delete(obj)
    db.commit()
    return None


@router.post("/{group_id}/vehicles/{vehicle_id}", response_model=Dict[str, Any])
def assign_vehicle_to_group(
    group_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    """Assign a vehicle to a vehicle group"""
    group = db.get(VehicleGroup, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle group not found"
        )
    
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    vehicle.vehicle_group_id = group_id
    db.commit()
    db.refresh(vehicle)
    
    return to_dict(vehicle)


@router.delete("/{group_id}/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_vehicle_from_group(
    group_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    """Remove a vehicle from a vehicle group"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    if vehicle.vehicle_group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is not in this group"
        )
    
    vehicle.vehicle_group_id = None
    db.commit()
    
    return None
