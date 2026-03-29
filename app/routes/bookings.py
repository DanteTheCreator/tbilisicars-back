from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, cast, String

from app.models.booking import Booking, BookingStatusEnum, Extra, BookingExtra
from app.models.booking_history import BookingHistory
from app.models.booking_vehicle_assignment import BookingVehicleAssignment
from app.models.user import User
from app.models.one_way_fee import OneWayFee
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.vehicle_model import VehicleModel
from app.models.vehicle_group import VehicleGroup
from app.models.brand import Brand
from app.models.rate import Rate, RateTier
from app.models.admin import Admin
from app.core.auth import get_optional_admin, get_current_super_admin
from app.core.email_sender import send_booking_confirmation
from app.core.contract_pdf import generate_contract_pdf
from .utils import get_db, to_dict, apply_updates
import re


def _find_or_create_user(db: Session, contact_email: str | None, contact_phone: str | None, 
                         contact_full_name: str) -> User:
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
    
    # Split full name into first and last for user model
    name_parts = contact_full_name.strip().split(maxsplit=1)
    first_name = name_parts[0] if name_parts else "Guest"
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
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
        # For new users, use email if provided, otherwise leave it as None
        user_email = contact_email if contact_email else None
        
        user = User(
            first_name=first_name,
            last_name=last_name,
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
        if user.first_name != first_name or user.last_name != last_name:
            user.first_name = first_name
            user.last_name = last_name
        if contact_phone and user.phone != contact_phone:
            user.phone = contact_phone
        if contact_email and user.email != contact_email:
            user.email = contact_email
    
    return user


def _validate_contact_payload(payload: dict, required: bool = False) -> None:
    """Validate contact fields in payload.

    - If required=True, must include contact_full_name (email is optional).
    - If email present, perform simple regex validation.
    Raises HTTPException(400) on invalid input.
    """
    from fastapi import HTTPException, status

    email = payload.get("contact_email", "").strip()
    full_name = payload.get("contact_full_name", "").strip()

    if required:
        missing = []
        if not full_name:
            missing.append("contact_full_name")
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing_fields": missing})

    # Basic email validation if provided and not empty
    # Allow any email format since some users don't have email and we input placeholders
    # if email:
    #     if not re.match(r"^[^@\s]+@[^@\s]+$", email):
    #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_email format")

    # Basic length checks
    if full_name and len(full_name) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_full_name too long")
    if payload.get("contact_phone") and len(payload.get("contact_phone")) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_phone too long")


def _calculate_one_way_fee(db: Session, pickup_location_id: int, dropoff_location_id: int) -> float:
    """
    Calculate one-way fee based on pickup and dropoff locations.
    Returns 0 if locations are the same or no fee is configured.
    """
    if pickup_location_id == dropoff_location_id:
        return 0.0
    
    # Try to find one-way fee by location IDs
    fee = db.query(OneWayFee).filter(
        OneWayFee.from_location_id == pickup_location_id,
        OneWayFee.to_location_id == dropoff_location_id,
        OneWayFee.is_active == True
    ).first()
    
    if fee:
        return float(fee.fee_amount)
    
    return 0.0


def _create_history_entry(
    db: Session,
    booking_id: int,
    action_type: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    description: str | None = None,
    changed_by_id: int | None = None
) -> None:
    """Create a booking history entry"""
    history = BookingHistory(
        booking_id=booking_id,
        changed_by_id=changed_by_id,
        changed_at=datetime.now(),
        action_type=action_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        description=description
    )
    db.add(history)
    db.flush()


def _handle_vehicle_change(
    db: Session,
    booking: Booking,
    vehicle_change_data: Dict[str, Any],
    admin_id: int | None = None
) -> None:
    """Handle vehicle change with proper assignment tracking"""
    change_date_str = vehicle_change_data.get('change_date')
    old_vehicle_id = vehicle_change_data.get('old_vehicle_id')
    new_vehicle_id = vehicle_change_data.get('new_vehicle_id')
    
    # Parse the change date as naive Tbilisi local time
    if isinstance(change_date_str, str):
        change_date = datetime.fromisoformat(change_date_str.replace('Z', '').replace('+00:00', ''))
    else:
        change_date = change_date_str or datetime.now()
    
    # Update existing vehicle assignment to end at change date
    if old_vehicle_id:
        # Find the active assignment for the old vehicle
        old_assignment = db.query(BookingVehicleAssignment).filter(
            BookingVehicleAssignment.booking_id == booking.id,
            BookingVehicleAssignment.vehicle_id == old_vehicle_id,
            BookingVehicleAssignment.end_date > change_date
        ).first()
        
        if old_assignment:
            # Update the end date to the change date
            old_assignment.end_date = change_date
            old_assignment.return_location_id = vehicle_change_data.get('return_location_id')
            old_assignment.odometer_reading = vehicle_change_data.get('odometer_reading')
            old_assignment.notes = vehicle_change_data.get('notes')
    
    # Create new vehicle assignment from change date to booking end
    if new_vehicle_id:
        new_assignment = BookingVehicleAssignment(
            booking_id=booking.id,
            vehicle_id=new_vehicle_id,
            start_date=change_date,
            end_date=booking.dropoff_datetime
        )
        db.add(new_assignment)
        # Always sync booking.vehicle_id with the latest assigned vehicle
        booking.vehicle_id = new_vehicle_id
    
    # Create history entry
    change_desc = (
        f"Vehicle changed from {vehicle_change_data.get('old_vehicle_info', 'N/A')} "
        f"to {vehicle_change_data.get('new_vehicle_info', 'N/A')} "
        f"on {change_date.strftime('%Y-%m-%d %H:%M')}. "
        f"Old vehicle returned at {vehicle_change_data.get('return_location_name', 'N/A')} "
        f"with odometer reading: {vehicle_change_data.get('odometer_reading', 'N/A')} km."
    )
    if vehicle_change_data.get('notes'):
        change_desc += f" Notes: {vehicle_change_data['notes']}"
    
    _create_history_entry(
        db=db,
        booking_id=booking.id,
        action_type="VEHICLE_CHANGED",
        field_name="vehicle_id",
        old_value=str(vehicle_change_data.get('old_vehicle_id', '')),
        new_value=str(vehicle_change_data.get('new_vehicle_id', '')),
        description=change_desc,
        changed_by_id=admin_id
    )


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
    
    # Try to find delivery fee from vehicle's location to pickup location
    if vehicle.location_id:
        fee = db.query(OneWayFee).filter(
            OneWayFee.from_location_id == vehicle.location_id,
            OneWayFee.to_location_id == pickup_location_id,
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
    
    # Calculate rental days – any partial day counts as a full day, minimum 2 days
    rental_days = math.ceil((dropoff_datetime - pickup_datetime).total_seconds() / 86400)
    if rental_days < 2:
        rental_days = 2
    
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
                RateTier.vehicle_model_id == vehicle.vehicle_model_id,
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
def list_bookings(
    db: Session = Depends(get_db), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(500, ge=1, le=10000),
    vehicle_id: Optional[int] = Query(None, description="Filter bookings by vehicle ID"),
    search: Optional[str] = Query(None, description="Search across contact name, email, phone, user name/email/phone, booking ID"),
    source: Optional[str] = Query(None, description="Filter by booking source: web, admin, broker"),
    exclude_source: Optional[str] = Query(None, description="Exclude bookings from this source"),
    include_archived: bool = Query(False, description="Include soft-deleted (archived) bookings")
):
    query = db.query(Booking)\
        .options(
            joinedload(Booking.vehicle).joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand),
            joinedload(Booking.vehicle_group),
            joinedload(Booking.vehicle_model).joinedload(VehicleModel.brand),
            joinedload(Booking.pickup_location),
            joinedload(Booking.dropoff_location),
            joinedload(Booking.user),
            joinedload(Booking.extras).joinedload(BookingExtra.extra)
        )
    
    # Exclude soft-deleted bookings (unless include_archived is set)
    if not include_archived:
        query = query.filter(Booking.deleted_at == None)

    # Server-side search across all relevant fields
    if search:
        term = f"%{search.strip()}%"
        # Digits-only version for phone matching (strip formatting)
        digits = re.sub(r'[\s\-\(\)\+]', '', search.strip())

        # User-side conditions via subquery (avoids conflicting with joinedload's join)
        user_conditions = [
            User.first_name.ilike(term),
            User.last_name.ilike(term),
            User.email.ilike(term),
            User.phone.ilike(term),
        ]
        if len(digits) >= 4:
            user_conditions.append(User.phone.ilike(f"%{digits}%"))
        user_match_ids = db.query(User.id).filter(or_(*user_conditions)).subquery()

        # Booking-side phone conditions
        phone_conditions = [Booking.contact_phone.ilike(term)]
        if len(digits) >= 4:
            phone_conditions.append(Booking.contact_phone.ilike(f"%{digits}%"))

        query = query.filter(
            or_(
                cast(Booking.id, String) == search.strip(),  # exact booking ID
                Booking.contact_full_name.ilike(term),
                Booking.contact_email.ilike(term),
                Booking.notes.ilike(term),
                Booking.broker.ilike(term),
                Booking.broker_id.ilike(term),
                Booking.user_id.in_(user_match_ids),
                *phone_conditions,
            )
        )

    # Consistent ordering
    query = query.order_by(Booking.id.desc())

    # Apply vehicle_id filter if provided
    # Include bookings currently assigned, via BookingVehicleAssignment, or historically assigned (booking_history)
    if vehicle_id is not None:
        assignment_booking_ids = db.query(BookingVehicleAssignment.booking_id).filter(
            BookingVehicleAssignment.vehicle_id == vehicle_id
        ).subquery()
        history_booking_ids = db.query(BookingHistory.booking_id).filter(
            BookingHistory.field_name == 'vehicle_id',
            or_(
                BookingHistory.old_value == str(vehicle_id),
                BookingHistory.new_value == str(vehicle_id),
            )
        ).subquery()
        query = query.filter(
            or_(
                Booking.vehicle_id == vehicle_id,
                Booking.id.in_(assignment_booking_ids),
                Booking.id.in_(history_booking_ids),
            )
        )
    
    # Apply source filter if provided
    if source is not None:
        query = query.filter(Booking.source == source)
    if exclude_source is not None:
        query = query.filter((Booking.source != exclude_source) | (Booking.source == None))

    items = query.offset(skip).limit(limit).all()
    
    # Manually serialize with relationships
    result = []
    for booking in items:
        booking_dict = to_dict(booking)
        
        # Add vehicle info
        if booking.vehicle:
            # Get make/model from vehicle_model if available, otherwise use legacy fields
            make = booking.vehicle.make or ''
            model = booking.vehicle.model or ''
            
            if booking.vehicle.vehicle_model:
                if booking.vehicle.vehicle_model.brand:
                    make = booking.vehicle.vehicle_model.brand.name
                model = booking.vehicle.vehicle_model.name
            
            booking_dict['vehicle'] = {
                'id': booking.vehicle.id,
                'make': make,
                'model': model,
                'year': booking.vehicle.year,
                'license_plate': booking.vehicle.license_plate
            }
        
        # Add vehicle group info (legacy)
        if booking.vehicle_group:
            booking_dict['vehicle_group'] = {
                'id': booking.vehicle_group.id,
                'name': booking.vehicle_group.name
            }
        
        # Add vehicle model info
        if booking.vehicle_model:
            brand_name = booking.vehicle_model.brand.name if booking.vehicle_model.brand else ''
            booking_dict['vehicle_model'] = {
                'id': booking.vehicle_model.id,
                'name': booking.vehicle_model.name,
                'brand': brand_name,
                'display_name': f"{brand_name} {booking.vehicle_model.name}".strip()
            }
        
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
        
        # Add extras info
        if booking.extras:
            booking_dict['extras'] = [
                {
                    'id': be.id,
                    'extra_id': be.extra_id,
                    'name': be.extra.name if be.extra else '',
                    'type': be.extra.type.value if be.extra and be.extra.type else '',
                    'quantity': be.quantity,
                    'daily_price': float(be.daily_price) if be.daily_price else 0,
                }
                for be in booking.extras
            ]

        result.append(booking_dict)
    
    return result


@router.get("/archived", response_model=List[Dict[str, Any]])
def list_archived_bookings(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """List all soft-deleted (archived) bookings. Super-admin only."""
    query = db.query(Booking)\
        .options(
            joinedload(Booking.vehicle).joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand),
            joinedload(Booking.vehicle_group),
            joinedload(Booking.vehicle_model).joinedload(VehicleModel.brand),
            joinedload(Booking.pickup_location),
            joinedload(Booking.dropoff_location),
            joinedload(Booking.user)
        )\
        .filter(Booking.deleted_at != None)\
        .order_by(Booking.deleted_at.desc())

    items = query.offset(skip).limit(limit).all()

    result = []
    for booking in items:
        booking_dict = to_dict(booking)
        if booking.vehicle:
            make = booking.vehicle.make or ''
            model = booking.vehicle.model or ''
            if booking.vehicle.vehicle_model:
                if booking.vehicle.vehicle_model.brand:
                    make = booking.vehicle.vehicle_model.brand.name
                model = booking.vehicle.vehicle_model.name
            booking_dict['vehicle'] = {
                'id': booking.vehicle.id,
                'make': make,
                'model': model,
                'year': booking.vehicle.year,
                'license_plate': booking.vehicle.license_plate,
            }
        if booking.vehicle_group:
            booking_dict['vehicle_group'] = {
                'id': booking.vehicle_group.id,
                'name': booking.vehicle_group.name,
            }
        if booking.vehicle_model:
            brand_name = booking.vehicle_model.brand.name if booking.vehicle_model.brand else ''
            booking_dict['vehicle_model'] = {
                'id': booking.vehicle_model.id,
                'name': booking.vehicle_model.name,
                'brand': brand_name,
                'display_name': f"{brand_name} {booking.vehicle_model.name}".strip()
            }
        if booking.pickup_location:
            booking_dict['pickup_location'] = {
                'id': booking.pickup_location.id,
                'name': booking.pickup_location.name,
                'city': booking.pickup_location.city,
            }
        if booking.dropoff_location:
            booking_dict['dropoff_location'] = {
                'id': booking.dropoff_location.id,
                'name': booking.dropoff_location.name,
                'city': booking.dropoff_location.city,
            }
        if booking.user:
            booking_dict['user'] = {
                'id': booking.user.id,
                'first_name': booking.user.first_name,
                'last_name': booking.user.last_name,
                'email': booking.user.email,
            }
        result.append(booking_dict)

    return result


@router.post("/{item_id}/restore", response_model=Dict[str, Any])
def restore_booking(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """Restore (unarchive) a soft-deleted booking. Super-admin only."""
    obj = db.query(Booking).filter(
        Booking.id == item_id,
        Booking.deleted_at != None,
    ).first()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived booking not found",
        )

    obj.deleted_at = None
    _create_history_entry(
        db=db,
        booking_id=obj.id,
        action_type="RESTORED",
        description=f"Booking restored from archive by admin {current_admin.username} (id={current_admin.id})",
        changed_by_id=current_admin.id,
    )
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_booking(item_id: int, db: Session = Depends(get_db)):
    obj = db.query(Booking).options(
        joinedload(Booking.pickup_location),
        joinedload(Booking.dropoff_location),
        joinedload(Booking.vehicle),
        joinedload(Booking.vehicle_group),
        joinedload(Booking.vehicle_model).joinedload(VehicleModel.brand)
    ).filter(Booking.id == item_id, Booking.deleted_at == None).first()
    
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    booking_dict = to_dict(obj)
    
    # Add location names
    if obj.pickup_location:
        booking_dict['pickup_location_name'] = obj.pickup_location.name
        if obj.pickup_location.city:
            booking_dict['pickup_location_name'] = f"{obj.pickup_location.name}, {obj.pickup_location.city}"
    
    if obj.dropoff_location:
        booking_dict['dropoff_location_name'] = obj.dropoff_location.name
        if obj.dropoff_location.city:
            booking_dict['dropoff_location_name'] = f"{obj.dropoff_location.name}, {obj.dropoff_location.city}"
    
    # Add vehicle info
    if obj.vehicle:
        booking_dict['vehicle_name'] = f"{obj.vehicle.make} {obj.vehicle.model} ({obj.vehicle.year})"
        booking_dict['vehicle_license_plate'] = obj.vehicle.license_plate
    
    # Add vehicle group name (legacy)
    if obj.vehicle_group:
        booking_dict['vehicle_group_name'] = obj.vehicle_group.name
    
    # Add vehicle model info
    if obj.vehicle_model:
        brand_name = obj.vehicle_model.brand.name if obj.vehicle_model.brand else ''
        booking_dict['vehicle_model_name'] = f"{brand_name} {obj.vehicle_model.name}".strip()
        booking_dict['vehicle_model'] = {
            'id': obj.vehicle_model.id,
            'name': obj.vehicle_model.name,
            'brand': brand_name,
            'display_name': f"{brand_name} {obj.vehicle_model.name}".strip()
        }
    
    # Add vehicle assignments with date ranges
    assignments = db.query(BookingVehicleAssignment).options(
        joinedload(BookingVehicleAssignment.vehicle),
        joinedload(BookingVehicleAssignment.return_location)
    ).filter(
        BookingVehicleAssignment.booking_id == item_id
    ).order_by(BookingVehicleAssignment.start_date).all()
    
    booking_dict['vehicle_assignments'] = []
    for assignment in assignments:
        assignment_dict = {
            'id': assignment.id,
            'vehicle_id': assignment.vehicle_id,
            'start_date': assignment.start_date.isoformat() if assignment.start_date else None,
            'end_date': assignment.end_date.isoformat() if assignment.end_date else None,
            'odometer_reading': assignment.odometer_reading,
            'notes': assignment.notes
        }
        if assignment.vehicle:
            assignment_dict['vehicle'] = {
                'id': assignment.vehicle.id,
                'make': assignment.vehicle.make,
                'model': assignment.vehicle.model,
                'year': assignment.vehicle.year,
                'license_plate': assignment.vehicle.license_plate
            }
        if assignment.return_location:
            assignment_dict['return_location'] = {
                'id': assignment.return_location.id,
                'name': assignment.return_location.name,
                'city': assignment.return_location.city
            }
        booking_dict['vehicle_assignments'].append(assignment_dict)
    
    return booking_dict


@router.get("/{item_id}/history", response_model=List[Dict[str, Any]])
def get_booking_history(item_id: int, db: Session = Depends(get_db)):
    """Get all history entries for a booking"""
    # Verify booking exists
    booking = db.get(Booking, item_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    # Query history with admin details
    history_entries = db.query(BookingHistory).filter(
        BookingHistory.booking_id == item_id
    ).order_by(BookingHistory.changed_at.desc()).all()
    
    result = []
    for entry in history_entries:
        entry_dict = {
            'id': entry.id,
            'booking_id': entry.booking_id,
            'changed_at': entry.changed_at.isoformat() if entry.changed_at else None,
            'action_type': entry.action_type,
            'field_name': entry.field_name,
            'old_value': entry.old_value,
            'new_value': entry.new_value,
            'description': entry.description,
            'changed_by': None
        }
        
        # If this is a vehicle change, enrich with vehicle details
        if entry.field_name == 'vehicle_id':
            if entry.old_value:
                try:
                    old_vehicle_id = int(entry.old_value)
                    old_vehicle = db.get(Vehicle, old_vehicle_id)
                    if old_vehicle:
                        entry_dict['old_value_display'] = f"{old_vehicle.license_plate} ({old_vehicle.make} {old_vehicle.model})"
                except (ValueError, TypeError):
                    pass
            
            if entry.new_value:
                try:
                    new_vehicle_id = int(entry.new_value)
                    new_vehicle = db.get(Vehicle, new_vehicle_id)
                    if new_vehicle:
                        entry_dict['new_value_display'] = f"{new_vehicle.license_plate} ({new_vehicle.make} {new_vehicle.model})"
                except (ValueError, TypeError):
                    pass
        
        if entry.changed_by:
            entry_dict['changed_by'] = {
                'id': entry.changed_by.id,
                'username': entry.changed_by.username,
                'email': entry.changed_by.email,
                'full_name': entry.changed_by.full_name
            }
        
        result.append(entry_dict)
    
    return result


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_booking(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
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
            contact_full_name=payload['contact_full_name']
        )
        print(f"[DEBUG] User created/found with id={user.id}")

    obj = Booking()
    apply_updates(obj, payload)
    
    # For web/public bookings (no admin), keep vehicle unassigned but preserve vehicle model
    is_web_booking = current_admin is None
    
    # Set booking source
    broker_val = payload.get('broker', '') or ''
    if is_web_booking:
        obj.source = 'web'
    elif broker_val and broker_val.lower() != 'web':
        obj.source = 'broker'
    else:
        obj.source = 'admin'

    if is_web_booking and obj.vehicle_id:
        # Look up the vehicle's model so we can set it on the booking
        vehicle = db.query(Vehicle).filter(Vehicle.id == obj.vehicle_id).first()
        if vehicle:
            if vehicle.vehicle_model_id:
                obj.vehicle_model_id = vehicle.vehicle_model_id
                print(f"[DEBUG] Web booking: set vehicle_model_id={vehicle.vehicle_model_id} from vehicle {vehicle.id}")
            if vehicle.vehicle_group_id:
                obj.vehicle_group_id = vehicle.vehicle_group_id
                print(f"[DEBUG] Web booking: set vehicle_group_id={vehicle.vehicle_group_id} from vehicle {vehicle.id}")
        # Clear vehicle_id — admin will assign a specific vehicle later
        obj.vehicle_id = None
        print(f"[DEBUG] Web booking: cleared vehicle_id (vehicle left unassigned)")
    
    # Set user_id directly if we created/found a user
    if user:
        print(f"[DEBUG] Setting obj.user_id = {user.id}")
        obj.user_id = user.id
    
    # Parse datetime strings as naive Tbilisi local time
    pickup_dt = obj.pickup_datetime
    dropoff_dt = obj.dropoff_datetime
    
    if isinstance(pickup_dt, str):
        pickup_dt = datetime.fromisoformat(pickup_dt.replace('Z', '').replace('+00:00', ''))
        obj.pickup_datetime = pickup_dt
    
    if isinstance(dropoff_dt, str):
        dropoff_dt = datetime.fromisoformat(dropoff_dt.replace('Z', '').replace('+00:00', ''))
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
    
    # Web bookings are auto-confirmed (customer sees "Confirmed" and contract reflects it)
    if is_web_booking:
        obj.status = BookingStatusEnum.CONFIRMED
    
    print(f"[DEBUG] Before commit: obj.user_id = {obj.user_id}")
    db.add(obj)
    try:
        db.commit()
        db.refresh(obj)
        
        # Create initial vehicle assignment if vehicle is assigned
        if obj.vehicle_id and obj.pickup_datetime and obj.dropoff_datetime:
            initial_assignment = BookingVehicleAssignment(
                booking_id=obj.id,
                vehicle_id=obj.vehicle_id,
                start_date=obj.pickup_datetime,
                end_date=obj.dropoff_datetime
            )
            db.add(initial_assignment)
        
        # Create initial history entry for booking creation
        status_display = _format_value_for_history(obj.status)
        admin_id = current_admin.id if current_admin else None
        _create_history_entry(
            db=db,
            booking_id=obj.id,
            action_type="CREATED",
            description=f"Booking created with status {status_display}",
            changed_by_id=admin_id
        )
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)

    # Send confirmation email for web bookings (in background so response is immediate)
    if is_web_booking and obj.contact_email:
        try:
            pickup_loc = obj.pickup_location.name if obj.pickup_location else "TBD"
            dropoff_loc = obj.dropoff_location.name if obj.dropoff_location else "TBD"
            # Use vehicle model name (e.g., "Toyota Prius") for the email
            vehicle_display_name = None
            if obj.vehicle_model_id:
                vm = db.query(VehicleModel).options(joinedload(VehicleModel.brand)).filter(VehicleModel.id == obj.vehicle_model_id).first()
                if vm:
                    brand_name = vm.brand.name if vm.brand else ''
                    vehicle_display_name = f"{brand_name} {vm.name}".strip()
            if not vehicle_display_name and obj.vehicle_group:
                vehicle_display_name = obj.vehicle_group.name
            rental_days = payload.get("rental_days")

            # Generate contract PDF to attach (still sync — fast, no network)
            try:
                pdf_bytes = _generate_booking_contract(db, obj)
            except Exception as pdf_err:
                print(f"[PDF] Error generating contract for booking #{obj.id}: {pdf_err}")
                pdf_bytes = None

            # Schedule the email to be sent AFTER the response is returned
            background_tasks.add_task(
                send_booking_confirmation,
                booking_id=obj.id,
                customer_name=obj.contact_full_name,
                customer_email=obj.contact_email,
                pickup_datetime=obj.pickup_datetime,
                dropoff_datetime=obj.dropoff_datetime,
                pickup_location=pickup_loc,
                dropoff_location=dropoff_loc,
                total_amount=float(obj.total_amount) if obj.total_amount else None,
                currency=obj.currency or "USD",
                rental_days=int(rental_days) if rental_days else None,
                vehicle_group_name=vehicle_display_name,
                pdf_attachment=pdf_bytes,
                one_way_fee=float(obj.one_way_fee) if obj.one_way_fee else 0.0,
                delivery_fee=float(obj.delivery_fee) if obj.delivery_fee else 0.0,
            )
        except Exception as e:
            print(f"[EMAIL] Error preparing confirmation for booking #{obj.id}: {e}")

    return to_dict(obj)


def _generate_booking_contract(db: Session, booking: Booking) -> bytes:
    """Load related objects and generate PDF contract for a booking."""
    vehicle = None
    if booking.vehicle_id:
        vehicle = db.query(Vehicle).options(
            joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand)
        ).filter(Vehicle.id == booking.vehicle_id).first()

    pickup_location = db.query(Location).get(booking.pickup_location_id) if booking.pickup_location_id else None
    dropoff_location = db.query(Location).get(booking.dropoff_location_id) if booking.dropoff_location_id else None
    user = db.query(User).get(booking.user_id) if booking.user_id else None

    extras = db.query(BookingExtra).options(
        joinedload(BookingExtra.extra)
    ).filter(BookingExtra.booking_id == booking.id).all()

    # Load vehicle group and vehicle model as fallback for contract display
    vehicle_group = None
    vehicle_model = None
    if booking.vehicle_group_id:
        vehicle_group = db.query(VehicleGroup).get(booking.vehicle_group_id)
    if booking.vehicle_model_id:
        vehicle_model = db.query(VehicleModel).options(
            joinedload(VehicleModel.brand)
        ).filter(VehicleModel.id == booking.vehicle_model_id).first()

    return generate_contract_pdf(
        booking=booking,
        vehicle=vehicle,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        extras=extras,
        user=user,
        vehicle_group=vehicle_group,
        vehicle_model=vehicle_model,
    )


@router.get("/{item_id}/contract", response_class=Response)
def download_booking_contract(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Download the rental contract PDF for a booking."""
    booking = db.query(Booking).filter(
        Booking.id == item_id,
        Booking.deleted_at == None
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    pdf_bytes = _generate_booking_contract(db, booking)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="TbilisiCars_Contract_TC-{item_id}.pdf"'
        },
    )


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_booking(
    item_id: int, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    obj = db.query(Booking).filter(Booking.id == item_id, Booking.deleted_at == None).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Prevent pickup (DELIVERED) without a vehicle assigned
    if payload.get('status') == 'DELIVERED' and not obj.vehicle_id:
        raise HTTPException(status_code=400, detail="Cannot make pickup without assigning a vehicle first")

    # If contact fields are supplied, validate them (not required on update)
    contact_keys = {"contact_full_name", "contact_email", "contact_phone"}
    if any(k in payload for k in contact_keys):
        _validate_contact_payload(payload, required=False)

    # Track changes for history
    tracked_fields = {
        'status': 'Booking Status',
        'payment_status': 'Payment Status',
        'vehicle_id': 'Vehicle',
        'vehicle_group_id': 'Vehicle Group',
        'vehicle_model_id': 'Vehicle Model',
        'pickup_location_id': 'Pickup Location',
        'dropoff_location_id': 'Dropoff Location',
        'pickup_datetime': 'Pickup Date/Time',
        'dropoff_datetime': 'Dropoff Date/Time',
        'total_amount': 'Total Amount',
        'broker': 'Broker',
        'broker_id': 'Broker ID',
        'notes': 'Notes'
    }
    
    changes = []
    for field, label in tracked_fields.items():
        if field in payload:
            old_val = getattr(obj, field, None)
            new_val = payload[field]
            old_val_formatted = _format_value_for_history(old_val)
            new_val_formatted = _format_value_for_history(new_val)
            if old_val_formatted != new_val_formatted:
                changes.append((field, label, old_val_formatted, new_val_formatted))

    # Handle vehicle change tracking BEFORE applying updates
    vehicle_change_data = payload.pop('_vehicle_change', None)
    
    apply_updates(obj, payload)
    
    # Recalculate one-way fee if locations changed
    if 'pickup_location_id' in payload or 'dropoff_location_id' in payload:
        if obj.pickup_location_id and obj.dropoff_location_id:
            one_way_fee = _calculate_one_way_fee(db, obj.pickup_location_id, obj.dropoff_location_id)
            obj.one_way_fee = one_way_fee
    
    # When booking is returned, update vehicle location to dropoff location
    if payload.get('status') == 'RETURNED' and obj.vehicle_id and obj.dropoff_location_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == obj.vehicle_id).first()
        if vehicle:
            vehicle.location_id = obj.dropoff_location_id
    
    # Create history entries for changes
    admin_id = current_admin.id if current_admin else None
    
    # Handle vehicle change with proper assignment tracking
    if vehicle_change_data:
        _handle_vehicle_change(db, obj, vehicle_change_data, admin_id)
    
    for field, label, old_val, new_val in changes:
        _create_history_entry(
            db=db,
            booking_id=item_id,
            action_type="FIELD_UPDATED",
            field_name=field,
            old_value=old_val,
            new_value=new_val,
            description=f"{label} changed from '{old_val}' to '{new_val}'",
            changed_by_id=admin_id
        )
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


def _format_value_for_history(value: Any) -> str | None:
    """Format a value for display in history, extracting enum values if needed."""
    if value is None:
        return None
    # Handle enums - extract the value/name
    if hasattr(value, 'value'):
        return str(value.value)
    if hasattr(value, 'name') and not isinstance(value, str):
        return str(value.name)
    return str(value)


@router.patch("/{item_id}", response_model=Dict[str, Any])
def partial_update_booking(
    item_id: int, 
    payload: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Partial update - same as PUT but semantically indicates partial updates"""
    obj = db.query(Booking).filter(Booking.id == item_id, Booking.deleted_at == None).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Prevent pickup (DELIVERED) without a vehicle assigned
    if payload.get('status') == 'DELIVERED' and not obj.vehicle_id:
        raise HTTPException(status_code=400, detail="Cannot make pickup without assigning a vehicle first")

    # If contact fields are supplied, validate them (not required on update)
    contact_keys = {"contact_full_name", "contact_email", "contact_phone"}
    if any(k in payload for k in contact_keys):
        _validate_contact_payload(payload, required=False)

    # Handle vehicle change tracking BEFORE applying updates
    vehicle_change_data = payload.pop('_vehicle_change', None)

    # Track changes for history
    tracked_fields = {
        'status': 'Booking Status',
        'payment_status': 'Payment Status',
        'vehicle_id': 'Vehicle',
        'vehicle_group_id': 'Vehicle Group',
        'vehicle_model_id': 'Vehicle Model',
        'pickup_location_id': 'Pickup Location',
        'dropoff_location_id': 'Dropoff Location',
        'pickup_datetime': 'Pickup Date/Time',
        'dropoff_datetime': 'Dropoff Date/Time',
        'total_amount': 'Total Amount',
        'broker': 'Broker',
        'broker_id': 'Broker ID',
        'notes': 'Notes'
    }
    
    changes = []
    for field, label in tracked_fields.items():
        if field in payload:
            old_val = getattr(obj, field, None)
            new_val = payload[field]
            old_val_formatted = _format_value_for_history(old_val)
            new_val_formatted = _format_value_for_history(new_val)
            if old_val_formatted != new_val_formatted:
                changes.append((field, label, old_val_formatted, new_val_formatted))

    apply_updates(obj, payload)
    
    # Recalculate one-way fee if locations changed
    if 'pickup_location_id' in payload or 'dropoff_location_id' in payload:
        if obj.pickup_location_id and obj.dropoff_location_id:
            one_way_fee = _calculate_one_way_fee(db, obj.pickup_location_id, obj.dropoff_location_id)
            obj.one_way_fee = one_way_fee
    
    # When booking is returned, update vehicle location to dropoff location
    if payload.get('status') == 'RETURNED' and obj.vehicle_id and obj.dropoff_location_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == obj.vehicle_id).first()
        if vehicle:
            vehicle.location_id = obj.dropoff_location_id
    
    # Create history entries for changes
    admin_id = current_admin.id if current_admin else None
    
    # Handle vehicle change with proper assignment tracking
    if vehicle_change_data:
        _handle_vehicle_change(db, obj, vehicle_change_data, admin_id)
    
    for field, label, old_val, new_val in changes:
        _create_history_entry(
            db=db,
            booking_id=item_id,
            action_type="FIELD_UPDATED",
            field_name=field,
            old_value=old_val,
            new_value=new_val,
            description=f"{label} changed from '{old_val}' to '{new_val}'",
            changed_by_id=admin_id
        )
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),  # Only super-admins (role="admin") may delete
):
    obj = db.query(Booking).filter(
        Booking.id == item_id,
        Booking.deleted_at == None
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Soft delete — stamp the timestamp and log to history instead of removing the row
    from datetime import datetime as _dt
    obj.deleted_at = _dt.now()
    _create_history_entry(
        db=db,
        booking_id=obj.id,
        action_type="ARCHIVED",
        description=f"Booking archived by admin {current_admin.username} (id={current_admin.id})",
        changed_by_id=current_admin.id,
    )
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
