from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.booking import Booking, Extra, BookingExtra
from app.models.user import User
from .utils import get_db, to_dict, apply_updates
import re


def _find_or_create_user(db: Session, contact_email: str, contact_phone: str | None, 
                         contact_first_name: str, contact_last_name: str) -> User:
    """
    Find an existing user by email or phone, or create a new guest user.
    Users are matched by email first, then by phone if email doesn't match.
    """
    # Try to find user by email
    user = db.query(User).filter(User.email == contact_email).first()
    
    if not user and contact_phone:
        # Try to find by phone if no email match
        user = db.query(User).filter(User.phone == contact_phone).first()
        
        # If found by phone but email is different, update the email
        if user and user.email != contact_email:
            user.email = contact_email
    
    # Create new user if not found
    if not user:
        user = User(
            first_name=contact_first_name,
            last_name=contact_last_name,
            email=contact_email,
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
    
    return user


def _validate_contact_payload(payload: dict, required: bool = False) -> None:
    """Validate contact fields in payload.

    - If required=True, must include contact_first_name, contact_last_name, contact_email.
    - If email present, perform simple regex validation.
    Raises HTTPException(400) on invalid input.
    """
    from fastapi import HTTPException, status

    email = payload.get("contact_email")
    first = payload.get("contact_first_name")
    last = payload.get("contact_last_name")

    if required:
        missing = [k for k in ("contact_first_name", "contact_last_name", "contact_email") if not payload.get(k)]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing_fields": missing})

    # Basic email validation if provided
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

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_bookings(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(Booking).offset(skip).limit(limit).all()
    return [to_dict(i) for i in items]


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
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Validate contact fields are present
    _validate_contact_payload(payload, required=True)
    
    # Find or create user from contact information
    # If user_id is not provided, we'll create/find one from contact info
    user = None
    if not payload.get('user_id'):
        print(f"[DEBUG] Creating/finding user for email={payload.get('contact_email')}, phone={payload.get('contact_phone')}")
        user = _find_or_create_user(
            db=db,
            contact_email=payload['contact_email'],
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
