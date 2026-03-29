from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from datetime import date, datetime
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_

from app.models.rate import Rate, RateTier, RateDayRange, RateHourRange, RateKmRange
from app.models.vehicle_group import VehicleGroup
from app.models.vehicle_model import VehicleModel
from app.models.brand import Brand
from app.models.vehicle import Vehicle
from app.models.location import Location
from app.models.one_way_fee import OneWayFee
from app.models.promo import Promo
from .utils import get_db, to_dict, apply_updates


def _find_applicable_promos(
    db: Session,
    pickup_date: date,
    rental_days: int,
    vehicle_group_id: int | None,
    rate_id: int | None,
    *,
    ignore_rate_filter: bool = False,
) -> List[Dict[str, Any]]:
    """Find all active promotions applicable to a booking's parameters."""
    query = db.query(Promo).filter(
        Promo.active == True,
        (Promo.start_date.is_(None)) | (Promo.start_date <= pickup_date),
        (Promo.end_date.is_(None)) | (Promo.end_date >= pickup_date),
        (Promo.min_days.is_(None)) | (Promo.min_days <= rental_days),
        (Promo.max_days.is_(None)) | (Promo.max_days >= rental_days),
    )

    # Filter by vehicle group: promo must target this group or be global (NULL)
    if vehicle_group_id is not None:
        query = query.filter(
            (Promo.vehicle_group_id == vehicle_group_id) | (Promo.vehicle_group_id.is_(None))
        )
    else:
        query = query.filter(Promo.vehicle_group_id.is_(None))

    # Filter by rate: promo must target this rate or be global (NULL)
    # When ignore_rate_filter is True (fallback pricing), include all promos
    # regardless of their rate linkage so discounts still apply.
    if not ignore_rate_filter:
        if rate_id is not None:
            query = query.filter(
                (Promo.rate_id == rate_id) | (Promo.rate_id.is_(None))
            )
        else:
            query = query.filter(Promo.rate_id.is_(None))

    return query.all()


def _apply_promos(
    base_price_per_day: float,
    rental_days: int,
    promos: list,
) -> tuple[float, float, List[Dict[str, Any]]]:
    """
    Apply all matching promotions to a base price.
    Returns (adjusted_price_per_day, total_promo_adjustment, promo_details).
    Positive promo value = surcharge/markup, negative = discount.
    """
    adjusted = base_price_per_day
    total_adjustment = 0.0
    details = []

    for p in promos:
        val = float(p.value)
        if p.discount_type.value == "PERCENT":
            # Percentage of base price per day
            change = round(base_price_per_day * val / 100, 2)
        else:
            # Fixed amount per day
            change = val

        adjusted += change
        total_adjustment += change * rental_days
        details.append({
            "promo_id": p.id,
            "promo_name": p.name,
            "discount_type": p.discount_type.value,
            "value": val,
            "per_day_change": change,
            "total_change": round(change * rental_days, 2),
        })

    # Don't let price go below 0
    if adjusted < 0:
        adjusted = 0.0

    return round(adjusted, 2), round(total_adjustment, 2), details

router = APIRouter(prefix="/rates", tags=["rates"])


# ============ Request/Response Models ============

class CalculatePriceRequest(BaseModel):
    vehicle_id: int
    pickup_date: str  # ISO format: "2025-11-10"
    dropoff_date: str  # ISO format: "2025-11-15"
    pickup_location_id: Optional[int] = None
    dropoff_location_id: Optional[int] = None


class CalculatePriceResponse(BaseModel):
    rate_id: Optional[int]
    rate_name: Optional[str]
    vehicle_model_id: Optional[int]
    vehicle_model_name: Optional[str]
    rental_days: int
    price_per_day: float
    base_total: float
    currency: str
    breakdown: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    fallback_price: Optional[float] = None


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


@router.get("/trip-prices", response_model=Dict[str, Any])
def trip_prices(
    pickup_date: str = Query(..., description="ISO date, e.g. 2025-11-10"),
    dropoff_date: str = Query(..., description="ISO date, e.g. 2025-11-15"),
    db: Session = Depends(get_db),
):
    """
    Return price_per_day and total_price for every vehicle_model_id.
    Uses the exact same rate-tier lookup as calculate-price: iterate rates
    by priority (newest first), take the FIRST matching tier per model.
    This is the single source of truth for listing-page prices.
    """

    # Parse dates
    try:
        pickup = datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
        dropoff = datetime.fromisoformat(dropoff_date.replace('Z', '+00:00'))
    except ValueError:
        pickup = datetime.strptime(pickup_date.split('T')[0], '%Y-%m-%d')
        dropoff = datetime.strptime(dropoff_date.split('T')[0], '%Y-%m-%d')

    rental_days = math.ceil((dropoff - pickup).total_seconds() / 86400)
    if rental_days < 2:
        rental_days = 2

    p_date = pickup.date()

    # Find active rates valid for the pickup date and matching duration,
    # ordered by priority (most recent first) — same as calculate-price
    applicable_rates = db.query(Rate).filter(
        and_(
            Rate.is_active == True,
            Rate.valid_from <= p_date,
            Rate.valid_until >= p_date,
            Rate.min_days <= rental_days,
            (Rate.max_days == None) | (Rate.max_days >= rental_days),
        )
    ).order_by(Rate.valid_from.desc(), Rate.id.desc()).all()

    if not applicable_rates:
        return {"prices": {}, "rental_days": rental_days}

    # For each rate (by priority), grab its matching tiers and assign to
    # vehicle models that haven't been assigned yet — first match wins.
    assigned: Dict[int, tuple] = {}  # vehicle_model_id -> (price_per_day, rate_id)

    for rate in applicable_rates:
        tiers = db.query(RateTier).filter(
            and_(
                RateTier.rate_id == rate.id,
                RateTier.from_days <= rental_days,
                (RateTier.to_days == None) | (RateTier.to_days >= rental_days),
            )
        ).all()

        for tier in tiers:
            mid = tier.vehicle_model_id
            if mid not in assigned:
                assigned[mid] = (float(tier.price_per_day), rate.id)

    prices = {}
    for mid, (ppd, matched_rate_id) in assigned.items():
        # Apply global promos (vehicle_group_id=NULL) and rate-specific promos
        promos = _find_applicable_promos(db, p_date, rental_days, None, matched_rate_id)
        adjusted_ppd, _, _ = _apply_promos(ppd, rental_days, promos)
        has_discount = bool(promos) and adjusted_ppd < ppd
        prices[str(mid)] = {
            "price_per_day": adjusted_ppd,
            "total_price": round(adjusted_ppd * rental_days, 2),
            "original_price_per_day": round(ppd, 2) if has_discount else None,
            "original_total_price": round(ppd * rental_days, 2) if has_discount else None,
        }

    return {"prices": prices, "rental_days": rental_days}


@router.get("/current-prices", response_model=Dict[str, Any])
def current_prices(db: Session = Depends(get_db)):
    """
    Return the lowest active rate price_per_day for each vehicle_model_id
    based on rates valid today. Used by the listing page to show accurate prices.
    """
    today = date.today()

    # Find all active rates valid today
    active_rates = db.query(Rate).filter(
        and_(
            Rate.is_active == True,
            Rate.valid_from <= today,
            Rate.valid_until >= today,
        )
    ).all()

    if not active_rates:
        return {"prices": {}}

    rate_ids = [r.id for r in active_rates]

    # Get the lowest price_per_day per vehicle_model_id from matching tiers
    from sqlalchemy import func
    rows = (
        db.query(
            RateTier.vehicle_model_id,
            func.min(RateTier.price_per_day).label("min_price"),
        )
        .filter(RateTier.rate_id.in_(rate_ids))
        .group_by(RateTier.vehicle_model_id)
        .all()
    )

    prices = {str(row.vehicle_model_id): float(row.min_price) for row in rows}
    return {"prices": prices}


@router.post("/calculate-price", response_model=Dict[str, Any])
def calculate_price(
    request: CalculatePriceRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate the rental price for a vehicle based on active rates.
    Returns the calculated price or falls back to vehicle group's base price if no rate found.
    """
    print(f"[DEBUG RATES START] request.pickup_date={request.pickup_date}, request.dropoff_date={request.dropoff_date}")
    print(f"[DEBUG RATES START] request.pickup_location_id={request.pickup_location_id}, request.dropoff_location_id={request.dropoff_location_id}")
    
    try:
        # 1. Get the vehicle with its model, group and location
        vehicle = db.query(Vehicle).options(
            joinedload(Vehicle.vehicle_group),
            joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand),
            joinedload(Vehicle.location)
        ).filter(Vehicle.id == request.vehicle_id).first()
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        # Calculate rental days first (needed for all cases)
        try:
            pickup = datetime.fromisoformat(request.pickup_date.replace('Z', '+00:00'))
            dropoff = datetime.fromisoformat(request.dropoff_date.replace('Z', '+00:00'))
        except ValueError:
            # Try parsing as date only
            pickup = datetime.strptime(request.pickup_date.split('T')[0], '%Y-%m-%d')
            dropoff = datetime.strptime(request.dropoff_date.split('T')[0], '%Y-%m-%d')
        
        rental_days = math.ceil((dropoff - pickup).total_seconds() / 86400)
        if rental_days < 2:
            rental_days = 2
        
        pickup_date = pickup.date()
        
        print(f"[DEBUG RATES] pickup={pickup}, dropoff={dropoff}, rental_days={rental_days}")
        print(f"[DEBUG RATES] pickup_location_id={request.pickup_location_id}, dropoff_location_id={request.dropoff_location_id}")
        
        # Calculate fees (works with or without vehicle group)
        one_way_fee = 0.0
        delivery_fee = 0.0
        
        # Calculate one-way fee if both locations provided
        if request.pickup_location_id and request.dropoff_location_id and request.pickup_location_id != request.dropoff_location_id:
            print(f"[DEBUG RATES] Different locations! Querying OneWayFee...")
            fee_record = db.query(OneWayFee).filter(
                OneWayFee.from_location_id == request.pickup_location_id,
                OneWayFee.to_location_id == request.dropoff_location_id,
                OneWayFee.is_active == True
            ).first()
            print(f"[DEBUG RATES] fee_record={fee_record}")
            if fee_record:
                one_way_fee = float(fee_record.fee_amount)
                print(f"[DEBUG RATES] one_way_fee={one_way_fee}")
        
        # Calculate delivery fee if vehicle is not at pickup location
        if request.pickup_location_id and vehicle.location_id and vehicle.location_id != request.pickup_location_id:
            fee_record = db.query(OneWayFee).filter(
                OneWayFee.from_location_id == vehicle.location_id,
                OneWayFee.to_location_id == request.pickup_location_id,
                OneWayFee.is_active == True
            ).first()
            if fee_record:
                delivery_fee = float(fee_record.fee_amount)
        
        if not vehicle.vehicle_model_id:
            # No vehicle model, fall back to starting_price
            fallback_price = float(vehicle.starting_price) if vehicle.starting_price else 50.0
            base_total = fallback_price * rental_days
            
            return {
                "error": "Vehicle has no vehicle model assigned",
                "fallback_price": fallback_price,
                "rental_days": rental_days,
                "price_per_day": fallback_price,
                "base_total": base_total,
                "one_way_fee": one_way_fee,
                "delivery_fee": delivery_fee,
                "total_with_fees": base_total + one_way_fee + delivery_fee,
                "currency": "EUR"
            }
        
        # Get vehicle model info
        vehicle_model = vehicle.vehicle_model
        vehicle_group = vehicle.vehicle_group
        model_display_name = f"{vehicle_model.brand.name} {vehicle_model.name}" if vehicle_model and vehicle_model.brand else (vehicle_model.name if vehicle_model else None)
        
        # 3. Find applicable rates
        # Query for active rates that:
        # - Are active
        # - Valid for the pickup date
        # - Support the rental duration
        # - Have a tier for this vehicle model
        applicable_rates = db.query(Rate).filter(
            and_(
                Rate.is_active == True,
                Rate.valid_from <= pickup_date,
                Rate.valid_until >= pickup_date,
                Rate.min_days <= rental_days,
                (Rate.max_days == None) | (Rate.max_days >= rental_days)
            )
        ).order_by(Rate.valid_from.desc(), Rate.id.desc()).all()
        
        # 4. Find the best matching rate tier
        selected_rate = None
        selected_tier = None
        
        for rate in applicable_rates:
            # Check if this rate has a tier for our vehicle model and rental duration
            tier = db.query(RateTier).filter(
                and_(
                    RateTier.rate_id == rate.id,
                    RateTier.vehicle_model_id == vehicle.vehicle_model_id,
                    RateTier.from_days <= rental_days,
                    (RateTier.to_days == None) | (RateTier.to_days >= rental_days)
                )
            ).first()
            
            if tier:
                selected_rate = rate
                selected_tier = tier
                break
        
        if selected_rate and selected_tier:
            price_per_day = float(selected_tier.price_per_day)
            base_total = price_per_day * rental_days

            # 5. Find and apply promotions
            vehicle_group_id = vehicle.vehicle_group.id if vehicle.vehicle_group else None
            promos = _find_applicable_promos(
                db, pickup_date, rental_days, vehicle_group_id, selected_rate.id
            )
            adjusted_ppd, promo_adjustment, promo_details = _apply_promos(
                price_per_day, rental_days, promos
            )
            adjusted_total = adjusted_ppd * rental_days

            return {
                "rate_id": selected_rate.id,
                "rate_name": selected_rate.name,
                "vehicle_model_id": vehicle.vehicle_model_id,
                "vehicle_model_name": model_display_name,
                "rental_days": rental_days,
                "price_per_day": adjusted_ppd,
                "original_price_per_day": price_per_day,
                "base_total": adjusted_total,
                "original_base_total": base_total,
                "promo_adjustment": promo_adjustment,
                "promos_applied": promo_details,
                "one_way_fee": one_way_fee,
                "delivery_fee": delivery_fee,
                "total_with_fees": adjusted_total + one_way_fee + delivery_fee,
                "currency": selected_tier.currency,
                "breakdown": {
                    "day_range": f"{selected_tier.from_days}-{selected_tier.to_days if selected_tier.to_days else 'unlimited'} days",
                    "from_days": selected_tier.from_days,
                    "to_days": selected_tier.to_days
                }
            }
        else:
            # No rate found, fallback to vehicle group's base price or vehicle starting_price
            fallback_price = 50.0
            if vehicle_group and vehicle_group.base_price_per_day:
                fallback_price = float(vehicle_group.base_price_per_day)
            elif vehicle.starting_price:
                fallback_price = float(vehicle.starting_price)
            
            # Still apply promos even when no rate tier matched
            vehicle_group_id = vehicle_group.id if vehicle_group else None
            promos = _find_applicable_promos(
                db, pickup_date, rental_days, vehicle_group_id, None,
                ignore_rate_filter=True,
            )
            adjusted_ppd, promo_adjustment, promo_details = _apply_promos(
                fallback_price, rental_days, promos
            )
            adjusted_total = adjusted_ppd * rental_days
            
            return {
                "error": "No active rate found for this vehicle and dates",
                "fallback_price": fallback_price,
                "rental_days": rental_days,
                "price_per_day": adjusted_ppd,
                "original_price_per_day": fallback_price,
                "base_total": adjusted_total,
                "original_base_total": fallback_price * rental_days,
                "promo_adjustment": promo_adjustment,
                "promos_applied": promo_details,
                "one_way_fee": one_way_fee,
                "delivery_fee": delivery_fee,
                "total_with_fees": adjusted_total + one_way_fee + delivery_fee,
                "currency": "EUR",
                "vehicle_model_id": vehicle.vehicle_model_id,
                "vehicle_model_name": model_display_name
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating price: {str(e)}"
        )


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
        RateTier.vehicle_model_id, RateTier.from_days
    ).all()
    
    return [to_dict(t) for t in tiers]


@router.get("/{item_id}/tiers/matrix", response_model=Dict[str, Any])
def get_rate_matrix(item_id: int, db: Session = Depends(get_db)):
    """
    Get rate pricing matrix organized by vehicle model and day range
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
    
    # Get vehicle models that have tiers
    vehicle_model_ids = list(set(t.vehicle_model_id for t in tiers if t.vehicle_model_id))
    vehicle_models = db.query(VehicleModel).options(
        joinedload(VehicleModel.brand)
    ).filter(
        VehicleModel.id.in_(vehicle_model_ids)
    ).all() if vehicle_model_ids else []
    
    # Organize into matrix
    matrix = {}
    for vm in vehicle_models:
        display_name = f"{vm.brand.name} {vm.name}" if vm.brand else vm.name
        matrix[display_name] = {
            "vehicle_model_id": vm.id,
            "prices": {}
        }
        
        # Find price for each day range
        for tier in tiers:
            if tier.vehicle_model_id == vm.id:
                range_key = f"{tier.from_days}-{tier.to_days if tier.to_days else 'unlimited'}"
                matrix[display_name]["prices"][range_key] = {
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
    
    # Verify vehicle model exists
    vehicle_model_id = payload.get('vehicle_model_id')
    if vehicle_model_id:
        vm = db.get(VehicleModel, vehicle_model_id)
        if not vm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle model not found"
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
    """Create multiple rate tiers at once. Deletes ALL existing tiers for this
    rate first so there are never stale duplicates — single source of truth."""
    # Verify rate exists
    rate = db.get(Rate, rate_id)
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found"
        )
    
    # Remove all existing tiers for this rate before inserting fresh ones
    db.query(RateTier).filter(RateTier.rate_id == rate_id).delete()
    
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
