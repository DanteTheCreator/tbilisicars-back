from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_

from app.models.rate import Rate, RateTier, RateDayRange, RateHourRange, RateKmRange
from app.models.vehicle_group import VehicleGroup
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_rates(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False)
):
    """List all rates with optional filtering"""
    query = db.query(Rate)
    
    if active_only:
        query = query.filter(Rate.is_active == True)
    
    query = query.order_by(Rate.name)
    items = query.offset(skip).limit(limit).all()
    
    return [to_dict(i) for i in items]


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_rate(item_id: int, db: Session = Depends(get_db), include_tiers: bool = Query(False)):
    """Get a specific rate by ID, optionally including tiers"""
    obj = db.get(Rate, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    result = to_dict(obj)
    
    if include_tiers:
        # Include rate tiers with vehicle group info
        tiers = db.query(RateTier).filter(RateTier.rate_id == item_id).all()
        result['tiers'] = [to_dict(t) for t in tiers]
        
        # Include day ranges
        day_ranges = db.query(RateDayRange).filter(
            RateDayRange.rate_id == item_id
        ).order_by(RateDayRange.from_days).all()
        result['day_ranges'] = [to_dict(dr) for dr in day_ranges]
        
        # Include hour ranges if any
        hour_ranges = db.query(RateHourRange).filter(RateHourRange.rate_id == item_id).all()
        result['hour_ranges'] = [to_dict(hr) for hr in hour_ranges]
        
        # Include km ranges if any
        km_ranges = db.query(RateKmRange).filter(RateKmRange.rate_id == item_id).all()
        result['km_ranges'] = [to_dict(kr) for kr in km_ranges]
    
    return result


@router.get("/{item_id}/tiers", response_model=List[Dict[str, Any]])
def get_rate_tiers(item_id: int, db: Session = Depends(get_db)):
    """Get all pricing tiers for a rate"""
    rate = db.get(Rate, item_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    tiers = db.query(RateTier).filter(RateTier.rate_id == item_id).order_by(
        RateTier.vehicle_group_id, RateTier.from_days
    ).all()
    
    return [to_dict(t) for t in tiers]


@router.get("/{item_id}/tiers/matrix", response_model=Dict[str, Any])
def get_rate_matrix(item_id: int, db: Session = Depends(get_db)):
    """
    Get rate pricing matrix organized by vehicle group and day range
    Returns a structured view like the screenshot
    """
    rate = db.get(Rate, item_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    # Get day ranges
    day_ranges = db.query(RateDayRange).filter(
        RateDayRange.rate_id == item_id
    ).order_by(RateDayRange.from_days).all()
    
    # Get all tiers
    tiers = db.query(RateTier).filter(RateTier.rate_id == item_id).all()
    
    # Get vehicle groups that have tiers
    vehicle_group_ids = list(set(t.vehicle_group_id for t in tiers))
    vehicle_groups = db.query(VehicleGroup).filter(
        VehicleGroup.id.in_(vehicle_group_ids)
    ).all()
    
    # Organize into matrix
    matrix = {}
    for vg in vehicle_groups:
        group_name = vg.name
        matrix[group_name] = {
            "vehicle_group_id": vg.id,
            "prices": {}
        }
        
        # Find price for each day range
        for tier in tiers:
            if tier.vehicle_group_id == vg.id:
                range_key = f"{tier.from_days}-{tier.to_days if tier.to_days else 'unlimited'}"
                matrix[group_name]["prices"][range_key] = {
                    "from_days": tier.from_days,
                    "to_days": tier.to_days,
                    "price_per_day": float(tier.price_per_day),
                    "currency": tier.currency
                }
    
    return {
        "rate_id": item_id,
        "rate_name": rate.name,
        "day_ranges": [to_dict(dr) for dr in day_ranges],
        "matrix": matrix
    }


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_rate(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new rate"""
    obj = Rate()
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
def update_rate(
    item_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a rate"""
    obj = db.get(Rate, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
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
def delete_rate(item_id: int, db: Session = Depends(get_db)):
    """Delete a rate (will cascade delete all tiers)"""
    obj = db.get(Rate, item_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    db.delete(obj)
    db.commit()
    return None


# ============ Rate Tier Endpoints ============

@router.post("/{rate_id}/tiers", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_rate_tier(
    rate_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Create a new rate tier (price for a vehicle group in a day range)"""
    # Verify rate exists
    rate = db.get(Rate, rate_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    # Verify vehicle group exists
    vehicle_group_id = payload.get('vehicle_group_id')
    if vehicle_group_id:
        vg = db.get(VehicleGroup, vehicle_group_id)
        if not vg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle group not found"
            )
    
    obj = RateTier()
    obj.rate_id = rate_id
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


@router.post("/{rate_id}/tiers/bulk", status_code=status.HTTP_201_CREATED)
def create_rate_tiers_bulk(
    rate_id: int,
    tiers: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Create multiple rate tiers at once (useful for setting up full pricing matrix)"""
    # Verify rate exists
    rate = db.get(Rate, rate_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    created_tiers = []
    for tier_data in tiers:
        obj = RateTier()
        obj.rate_id = rate_id
        apply_updates(obj, tier_data)
        db.add(obj)
        created_tiers.append(obj)
    
    try:
        db.commit()
        for obj in created_tiers:
            db.refresh(obj)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e.orig) if getattr(e, "orig", None) else str(e)
        )
    
    return {
        "created_count": len(created_tiers),
        "tiers": [to_dict(t) for t in created_tiers]
    }


@router.put("/tiers/{tier_id}", response_model=Dict[str, Any])
def update_rate_tier(
    tier_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a specific rate tier"""
    obj = db.get(RateTier, tier_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate tier not found"
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


@router.delete("/tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate_tier(tier_id: int, db: Session = Depends(get_db)):
    """Delete a rate tier"""
    obj = db.get(RateTier, tier_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate tier not found"
        )
    db.delete(obj)
    db.commit()
    return None


# ============ Day Range Endpoints ============

@router.post("/{rate_id}/day-ranges", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_day_range(
    rate_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Create a day range for a rate"""
    rate = db.get(Rate, rate_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    obj = RateDayRange()
    obj.rate_id = rate_id
    apply_updates(obj, payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.get("/{rate_id}/day-ranges", response_model=List[Dict[str, Any]])
def get_day_ranges(rate_id: int, db: Session = Depends(get_db)):
    """Get all day ranges for a rate"""
    rate = db.get(Rate, rate_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    ranges = db.query(RateDayRange).filter(
        RateDayRange.rate_id == rate_id
    ).order_by(RateDayRange.from_days).all()
    
    return [to_dict(r) for r in ranges]


@router.delete("/day-ranges/{range_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_day_range(range_id: int, db: Session = Depends(get_db)):
    """Delete a day range"""
    obj = db.get(RateDayRange, range_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Day range not found"
        )
    db.delete(obj)
    db.commit()
    return None
