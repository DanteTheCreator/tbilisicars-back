from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

from app.models.booking import Booking, Extra, BookingExtra
from app.models.user import User
from app.models.one_way_fee import OneWayFee
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.rate import Rate, RateTier
from .utils import get_db, to_dict, apply_updates
import re


def _find_or_create_user(db: Session, contact_email: str | None, contact_phone: str | None, 
                         contact_first_name: str, contact_last_name: str) -> User:
    """
    Find an existing user by email or phone, or create a new guest user.
    Users are matched by email first (if provided), then by phone if email doesn't match.
    At least one of email or phone should be provided for identification.
    """
    user = None
    
    # Normalize empty strings to None
    contact_email = contact_email.strip() if contact_email else None
    contact_email = contact_email if contact_email else None  # Convert empty string to None
    contact_phone = contact_phone.strip() if contact_phone else None
    contact_phone = contact_phone if contact_phone else None  # Convert empty string to None
    
    # Try to find user by email if provided
    if contact_email:
        user = db.query(User).filter(User.email == contact_email).first()
    
    if not user and contact_phone:
        # Try to find by phone if no email match
        user = db.query(User).filter(User.phone == contact_phone).first()
        
        # If found by phone but email is different (and email was provided), update the email
        if user and contact_email and user.email != contact_email:
            user.email = contact_email
    
    # Create new user if not found
    if not user:
        # For new users, use email if provided, otherwise use a placeholder
        # based on phone or a timestamp
        user_email = contact_email
        if not user_email:
            # If no email, create a placeholder email using phone or timestamp
            if contact_phone:
                # Use phone-based email
                user_email = f"guest_{contact_phone.replace('+', '').replace(' ', '')}@tbilisicars.local"
            else:
                # Use timestamp-based email as last resort
                from datetime import datetime
                user_email = f"guest_{int(datetime.utcnow().timestamp())}@tbilisicars.local"
        
        user = User(
            first_name=contact_first_name,
            last_name=contact_last_name,
            email=user_email,
            phone=contact_phone,
            hashed_password=None,  # Guest users don't have passwords
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        db.flush()  # Get the user ID without committing yet
    else:
        # Update user info if it changed
        if user.first_name != contact_first_name or user.last_name != contact_last_name:
            user.first_name = contact_first_name
            user.last_name = contact_last_name
        if contact_phone and user.phone != contact_phone:
            user.phone = contact_phone
        if contact_email and user.email != contact_email:
            user.email = contact_email
    
    return user


def _validate_contact_payload(payload: dict, required: bool = False) -> None:
    """Validate contact fields in payload.

    - If required=True, must include contact_first_name and contact_last_name (email is optional).
    - If email present, perform simple regex validation.
    Raises HTTPException(400) on invalid input.
    """
    from fastapi import HTTPException, status

    email = payload.get("contact_email", "").strip()
    first = payload.get("contact_first_name", "").strip()
    last = payload.get("contact_last_name", "").strip()

    if required:
        missing = []
        if not first:
            missing.append("contact_first_name")
        if not last:
            missing.append("contact_last_name")
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing_fields": missing})

    # Basic email validation if provided and not empty
    if email:
        # simple regex; not exhaustive but sufficient for basic validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_email format")

    # Basic length checks
    if first and len(first) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_first_name too long")
    if last and len(last) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_last_name too long")
    if payload.get("contact_phone") and len(payload.get("contact_phone")) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_phone too long")


def _calculate_one_way_fee(db: Session, pickup_location_id: int, dropoff_location_id: int) -> float:
    """
    Calculate one-way fee based on pickup and dropoff locations.
    Returns 0 if locations are in the same city or no fee is configured.
    """
    if pickup_location_id == dropoff_location_id:
        return 0.0
    
    # Get location cities
    pickup_loc = db.query(Location).filter(Location.id == pickup_location_id).first()
    dropoff_loc = db.query(Location).filter(Location.id == dropoff_location_id).first()
    
    if not pickup_loc or not dropoff_loc:
        return 0.0
    
    # If cities are the same, no one-way fee
    if pickup_loc.city and dropoff_loc.city and pickup_loc.city.lower() == dropoff_loc.city.lower():
        return 0.0
    
    # Try to find one-way fee
    if pickup_loc.city and dropoff_loc.city:
        fee = db.query(OneWayFee).filter(
            OneWayFee.from_city.ilike(pickup_loc.city),
            OneWayFee.to_city.ilike(dropoff_loc.city),
            OneWayFee.is_active == True
        ).first()
        
        if fee:
            return float(fee.fee_amount)
    
    return 0.0


def _calculate_delivery_fee(db: Session, vehicle_id: int, pickup_location_id: int) -> float:
    """
    Calculate delivery fee if vehicle's current location is different from pickup location.
    Returns 0 if same city or no fee is configured.
    """
    # Get vehicle with its current location
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.location)).filter(Vehicle.id == vehicle_id).first()
    if not vehicle or not vehicle.location_id:
        return 0.0
    
    # If vehicle is already at pickup location, no delivery fee
    if vehicle.location_id == pickup_location_id:
        return 0.0
    
    # Get pickup location
    pickup_loc = db.query(Location).filter(Location.id == pickup_location_id).first()
    
    if not vehicle.location or not pickup_loc:
        return 0.0
    
    # If cities are the same, no delivery fee
    if vehicle.location.city and pickup_loc.city and vehicle.location.city.lower() == pickup_loc.city.lower():
        return 0.0
    
    # Try to find delivery fee from vehicle's city to pickup city
    if vehicle.location.city and pickup_loc.city:
        fee = db.query(OneWayFee).filter(
            OneWayFee.from_city.ilike(vehicle.location.city),
            OneWayFee.to_city.ilike(pickup_loc.city),
            OneWayFee.is_active == True
        ).first()
        
        if fee:
            return float(fee.fee_amount)
    
    return 0.0


def _calculate_rate_for_booking(
    db: Session,
    vehicle_id: int,
    pickup_datetime: datetime,
    dropoff_datetime: datetime
) -> Tuple[Optional[int], Optional[int], float]:
    """
    Calculate rate for a booking. Returns (rate_id, rate_tier_id, price_per_day).
    Falls back to vehicle group's base_price_per_day or vehicle.starting_price if no rate is found.
    """
    # Get vehicle and its group
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.vehicle_group)).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return (None, None, 50.0)  # Default fallback
    
    if not vehicle.vehicle_group_id:
        # No vehicle group, use vehicle's starting_price
        return (None, None, float(vehicle.starting_price) if vehicle.starting_price else 50.0)
    
    # Calculate rental days
    rental_days = (dropoff_datetime - pickup_datetime).days
    if rental_days < 1:
        rental_days = 1
    
    pickup_date = pickup_datetime.date()
    
    # Find applicable rates
    applicable_rates = db.query(Rate).filter(
        and_(
            Rate.is_active == True,
            Rate.valid_from <= pickup_date,
            Rate.valid_until >= pickup_date,
            Rate.min_days <= rental_days,
            (Rate.max_days == None) | (Rate.max_days >= rental_days)
        )
    ).order_by(Rate.valid_from.desc(), Rate.id.desc()).all()
    
    # Find the best matching rate tier
    for rate in applicable_rates:
        tier = db.query(RateTier).filter(
            and_(
                RateTier.rate_id == rate.id,
                RateTier.vehicle_group_id == vehicle.vehicle_group_id,
                RateTier.from_days <= rental_days,
                (RateTier.to_days == None) | (RateTier.to_days >= rental_days)
            )
        ).first()
        
        if tier:
            return (rate.id, tier.id, float(tier.price_per_day))
    
    # No rate found, fallback to vehicle group's base price or vehicle starting_price
    if vehicle.vehicle_group and vehicle.vehicle_group.base_price_per_day:
        return (None, None, float(vehicle.vehicle_group.base_price_per_day))
    return (None, None, float(vehicle.starting_price) if vehicle.starting_price else 50.0)


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_bookings(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(Booking)\
        .options(
            joinedload(Booking.vehicle),
            joinedload(Booking.vehicle_group),
            joinedload(Booking.pickup_location),
            joinedload(Booking.dropoff_location),
            joinedload(Booking.user)
        )\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    # Manually serialize with relationships
    result = []
    for booking in items:
        booking_dict = to_dict(booking)
        
        # Add vehicle info
        if booking.vehicle:
            booking_dict['vehicle'] = {
                'id': booking.vehicle.id,
                'make': booking.vehicle.make,
                'model': booking.vehicle.model,
                'year': booking.vehicle.year,
                'license_plate': booking.vehicle.license_plate
            }
        
        # Add vehicle group info
        print(f"[DEBUG] Booking {booking.id}: vehicle_group_id={booking.vehicle_group_id}, has vehicle_group={booking.vehicle_group is not None}")
        if booking.vehicle_group:
            print(f"[DEBUG] Adding vehicle_group: id={booking.vehicle_group.id}, name={booking.vehicle_group.name}")
            booking_dict['vehicle_group'] = {
                'id': booking.vehicle_group.id,
                'name': booking.vehicle_group.name
            }
        else:
            print(f"[DEBUG] No vehicle_group for booking {booking.id}")
        
        # Add pickup location info
        if booking.pickup_location:
            booking_dict['pickup_location'] = {
                'id': booking.pickup_location.id,
                'name': booking.pickup_location.name,
                'city': booking.pickup_location.city
            }
        
        # Add dropoff location info
        if booking.dropoff_location:
            booking_dict['dropoff_location'] = {
                'id': booking.dropoff_location.id,
                'name': booking.dropoff_location.name,
                'city': booking.dropoff_location.city
            }
        
        # Add user info
        if booking.user:
            booking_dict['user'] = {
                'id': booking.user.id,
                'first_name': booking.user.first_name,
                'last_name': booking.user.last_name,
                'email': booking.user.email
            }
        
        result.append(booking_dict)
    
    return result


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_booking(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Booking, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return to_dict(obj)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_booking(request: Request, db: Session = Depends(get_db)):
    # Check content type to provide better error message
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        raise HTTPException(
            status_code=400,
            detail="This endpoint expects JSON data. For photo uploads, use POST /api/bookings/{booking_id}/photos after creating the booking."
        )
    
    # Parse JSON payload
    try:
        payload = await request.json()
        print(f"[DEBUG] Received booking payload: {payload}")
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Validate contact fields are present
    try:
        _validate_contact_payload(payload, required=True)
    except HTTPException as e:
        print(f"[ERROR] Validation failed: {e.detail}")
        raise
    
    # Find or create user from contact information
    # If user_id is not provided, we'll create/find one from contact info
    user = None
    if not payload.get('user_id'):
        print(f"[DEBUG] Creating/finding user for email={payload.get('contact_email')}, phone={payload.get('contact_phone')}")
        user = _find_or_create_user(
            db=db,
            contact_email=payload.get('contact_email'),
            contact_phone=payload.get('contact_phone'),
            contact_first_name=payload['contact_first_name'],
            contact_last_name=payload['contact_last_name']
        )
        print(f"[DEBUG] User created/found with id={user.id}")

    obj = Booking()
    apply_updates(obj, payload)
    
    # Set user_id directly if we created/found a user
    if user:
        print(f"[DEBUG] Setting obj.user_id = {user.id}")
        obj.user_id = user.id
    
    # Parse datetime strings if they are strings
    pickup_dt = obj.pickup_datetime
    dropoff_dt = obj.dropoff_datetime
    
    if isinstance(pickup_dt, str):
        pickup_dt = datetime.fromisoformat(pickup_dt.replace('Z', '+00:00'))
        obj.pickup_datetime = pickup_dt
    
    if isinstance(dropoff_dt, str):
        dropoff_dt = datetime.fromisoformat(dropoff_dt.replace('Z', '+00:00'))
        obj.dropoff_datetime = dropoff_dt
    
    # Calculate and set rate information if vehicle and dates are provided
    if obj.vehicle_id and obj.pickup_datetime and obj.dropoff_datetime:
        rate_id, rate_tier_id, price_per_day = _calculate_rate_for_booking(
            db, obj.vehicle_id, obj.pickup_datetime, obj.dropoff_datetime
        )
        obj.rate_id = rate_id
        obj.rate_tier_id = rate_tier_id
        obj.price_per_day = price_per_day
        print(f"[DEBUG] Rate calculated: rate_id={rate_id}, tier_id={rate_tier_id}, price_per_day={price_per_day}")
    
    # Calculate and set delivery fee if vehicle and pickup location are provided
    if obj.vehicle_id and obj.pickup_location_id:
        delivery_fee = _calculate_delivery_fee(db, obj.vehicle_id, obj.pickup_location_id)
        obj.delivery_fee = delivery_fee
        print(f"[DEBUG] Delivery fee calculated: {delivery_fee}")
    
    # Calculate and set one-way fee if locations are provided
    if obj.pickup_location_id and obj.dropoff_location_id:
        one_way_fee = _calculate_one_way_fee(db, obj.pickup_location_id, obj.dropoff_location_id)
        obj.one_way_fee = one_way_fee
        print(f"[DEBUG] One-way fee calculated: {one_way_fee}")
    
    print(f"[DEBUG] Before commit: obj.user_id = {obj.user_id}")
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_booking(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(Booking, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    # If contact fields are supplied, validate them (not required on update)
    contact_keys = {"contact_first_name", "contact_last_name", "contact_email", "contact_phone"}
    if any(k in payload for k in contact_keys):
        _validate_contact_payload(payload, required=False)

    apply_updates(obj, payload)
    
    # Recalculate one-way fee if locations changed
    if 'pickup_location_id' in payload or 'dropoff_location_id' in payload:
        if obj.pickup_location_id and obj.dropoff_location_id:
            one_way_fee = _calculate_one_way_fee(db, obj.pickup_location_id, obj.dropoff_location_id)
            obj.one_way_fee = one_way_fee
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.patch("/{item_id}", response_model=Dict[str, Any])
def partial_update_booking(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Partial update - same as PUT but semantically indicates partial updates"""
    obj = db.get(Booking, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    # If contact fields are supplied, validate them (not required on update)
    contact_keys = {"contact_first_name", "contact_last_name", "contact_email", "contact_phone"}
    if any(k in payload for k in contact_keys):
        _validate_contact_payload(payload, required=False)

    apply_updates(obj, payload)
    
    # Recalculate one-way fee if locations changed
    if 'pickup_location_id' in payload or 'dropoff_location_id' in payload:
        if obj.pickup_location_id and obj.dropoff_location_id:
            one_way_fee = _calculate_one_way_fee(db, obj.pickup_location_id, obj.dropoff_location_id)
            obj.one_way_fee = one_way_fee
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Booking, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    db.delete(obj)
    db.commit()
    return None


# Extras sub-resources (basic CRUD for Extra and BookingExtra)
extra_router = APIRouter(prefix="/extras", tags=["extras"])


@extra_router.get("/", response_model=List[Dict[str, Any]])
def list_extras(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(Extra).offset(skip).limit(limit).all()
    return [to_dict(i) for i in items]


@extra_router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_extra(payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = Extra()
    apply_updates(obj, payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@extra_router.put("/{item_id}", response_model=Dict[str, Any])
def update_extra(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(Extra, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extra not found")
    apply_updates(obj, payload)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@extra_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_extra(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Extra, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extra not found")
    db.delete(obj)
    db.commit()
    return None


# BookingExtra
booking_extra_router = APIRouter(prefix="/booking-extras", tags=["booking-extras"])


@booking_extra_router.get("/", response_model=List[Dict[str, Any]])
def list_booking_extras(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(BookingExtra).offset(skip).limit(limit).all()
    return [to_dict(i) for i in items]


@booking_extra_router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_booking_extra(payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = BookingExtra()
    apply_updates(obj, payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@booking_extra_router.put("/{item_id}", response_model=Dict[str, Any])
def update_booking_extra(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(BookingExtra, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BookingExtra not found")
    apply_updates(obj, payload)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@booking_extra_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking_extra(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(BookingExtra, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BookingExtra not found")
    db.delete(obj)
    db.commit()
    return None
