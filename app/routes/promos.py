from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.promo import Promo, BookingPromo
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/promos", tags=["promos"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_promos(
    db: Session = Depends(get_db), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    vehicle_group_id: int | None = Query(None)
):
    """List all promos with optional filters"""
    query = db.query(Promo)
    
    if active_only:
        today = date.today()
        query = query.filter(Promo.active == True)
        query = query.filter(
            (Promo.start_date.is_(None)) | (Promo.start_date <= today)
        )
        query = query.filter(
            (Promo.end_date.is_(None)) | (Promo.end_date >= today)
        )
    
    if vehicle_group_id is not None:
        query = query.filter(
            (Promo.vehicle_group_id == vehicle_group_id) | (Promo.vehicle_group_id.is_(None))
        )
    
    items = query.offset(skip).limit(limit).all()
    return [to_dict(i) for i in items]


@router.get("/vehicle-group/{vehicle_group_id}", response_model=List[Dict[str, Any]])
def get_active_promos_for_vehicle_group(
    vehicle_group_id: int, 
    rental_days: int | None = Query(None),
    db: Session = Depends(get_db)
):
    """Get active promotions applicable to a specific vehicle group"""
    today = date.today()
    
    query = db.query(Promo).filter(
        Promo.active == True,
        (Promo.vehicle_group_id == vehicle_group_id) | (Promo.vehicle_group_id.is_(None)),
        (Promo.start_date.is_(None)) | (Promo.start_date <= today),
        (Promo.end_date.is_(None)) | (Promo.end_date >= today)
    )
    
    if rental_days is not None:
        query = query.filter(
            (Promo.min_days.is_(None)) | (Promo.min_days <= rental_days),
            (Promo.max_days.is_(None)) | (Promo.max_days >= rental_days)
        )
    
    items = query.all()
    return [to_dict(i) for i in items]


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_promo(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Promo, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found")
    return to_dict(obj)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_promo(payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = Promo()
    apply_updates(obj, payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_promo(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(Promo, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found")
    apply_updates(obj, payload)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promo(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Promo, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found")
    db.delete(obj)
    db.commit()
    return None
