from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.models.vehicle import Vehicle
from app.models.booking import Booking
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def get_photo_url(object_name: str) -> str:
    """Generate public URL for a photo stored in MinIO"""
    # Get MinIO settings from environment
    public_endpoint = os.getenv('MINIO_PUBLIC_ENDPOINT', 'tbilisicars.live:9000')
    public_secure = os.getenv('MINIO_PUBLIC_SECURE', 'true').lower() == 'true'
    protocol = "https" if public_secure else "http"
    bucket = os.getenv('MINIO_VEHICLE_PHOTOS_BUCKET', 'vehicle-photos')
    return f"{protocol}://{public_endpoint}/{bucket}/{object_name}"


@router.get("/", response_model=List[Dict[str, Any]])
def list_vehicles(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(Vehicle).options(
        joinedload(Vehicle.location), 
        joinedload(Vehicle.photos),
        joinedload(Vehicle.vehicle_group)
    ).offset(skip).limit(limit).all()
    result = []
    for item in items:
        vehicle_dict = to_dict(item)
        if item.location:
            vehicle_dict['location_name'] = item.location.name
            vehicle_dict['location_full_name'] = f"{item.location.name}, {item.location.city}" if item.location.city else item.location.name
        else:
            vehicle_dict['location_name'] = None
            vehicle_dict['location_full_name'] = None
        
        # Add photos with URLs
        if item.photos:
            vehicle_dict['photos'] = [
                {
                    'id': photo.id,
                    'url': get_photo_url(photo.object_name),
                    'object_name': photo.object_name,
                    'is_primary': photo.is_primary,
                    'display_order': photo.display_order,
                    'alt_text': photo.alt_text,
                }
                for photo in item.photos
            ]
        else:
            vehicle_dict['photos'] = []
        
        # Add vehicle group pricing information
        if item.vehicle_group:
            vehicle_dict['vehicle_group_name'] = item.vehicle_group.name
            vehicle_dict['vehicle_group_id'] = item.vehicle_group.id
            # Use vehicle group's base price if vehicle doesn't have starting_price set
            if item.vehicle_group.base_price_per_day is not None:
                if item.starting_price is None or item.starting_price == 50.00:  # 50.00 is the default
                    vehicle_dict['starting_price'] = float(item.vehicle_group.base_price_per_day)
        
        result.append(vehicle_dict)
    return result


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_vehicle(item_id: int, db: Session = Depends(get_db)):
    obj = db.query(Vehicle).options(
        joinedload(Vehicle.location), 
        joinedload(Vehicle.photos),
        joinedload(Vehicle.vehicle_group)
    ).filter(Vehicle.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    vehicle_dict = to_dict(obj)
    if obj.location:
        vehicle_dict['location_name'] = obj.location.name
        vehicle_dict['location_full_name'] = f"{obj.location.name}, {obj.location.city}" if obj.location.city else obj.location.name
    else:
        vehicle_dict['location_name'] = None
        vehicle_dict['location_full_name'] = None
    
    # Add photos with URLs
    if obj.photos:
        vehicle_dict['photos'] = [
            {
                'id': photo.id,
                'url': get_photo_url(photo.object_name),
                'object_name': photo.object_name,
                'is_primary': photo.is_primary,
                'display_order': photo.display_order,
                'alt_text': photo.alt_text,
            }
            for photo in obj.photos
        ]
    else:
        vehicle_dict['photos'] = []
    
    # Add vehicle group pricing information
    if obj.vehicle_group:
        vehicle_dict['vehicle_group_name'] = obj.vehicle_group.name
        vehicle_dict['vehicle_group_id'] = obj.vehicle_group.id
        # Use vehicle group's base price if vehicle doesn't have starting_price set
        if obj.vehicle_group.base_price_per_day is not None:
            if obj.starting_price is None or obj.starting_price == 50.00:  # 50.00 is the default
                vehicle_dict['starting_price'] = float(obj.vehicle_group.base_price_per_day)
    
    return vehicle_dict


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_vehicle(payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = Vehicle()
    apply_updates(obj, payload)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_vehicle(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(Vehicle, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    apply_updates(obj, payload)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Vehicle, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    
    # Set vehicle_id to NULL for all bookings with this vehicle
    db.query(Booking).filter(Booking.vehicle_id == item_id).update(
        {"vehicle_id": None},
        synchronize_session=False
    )
    
    # Delete the vehicle
    db.delete(obj)
    db.commit()
    return None
