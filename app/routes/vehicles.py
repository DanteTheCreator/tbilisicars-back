from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from sqlalchemy import and_

from app.models.vehicle import Vehicle, VehicleStatusEnum
from app.models.vehicle_model import VehicleModel
from app.models.vehicle_history import VehicleHistory
from app.models.booking import Booking, BookingStatusEnum
from app.models.rate import Rate, RateTier
from app.models.document import VehicleDocument, DocumentTypeEnum
from app.core.minio import minio_client
from .utils import get_db, to_dict, apply_updates
from .auth import get_current_admin

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def get_photo_url(object_name: str) -> str:
    """Generate public URL for a photo stored in MinIO.
    
    Uses the main domain with nginx proxy (/vehicle-photos/) so photos
    are served through port 443 instead of requiring direct MinIO port 9000 access.
    """
    base_url = os.getenv('PHOTO_BASE_URL', 'https://tbilisicars.live')
    bucket = os.getenv('MINIO_VEHICLE_PHOTOS_BUCKET', 'vehicle-photos')
    return f"{base_url}/{bucket}/{object_name}"


def _create_history_entry(
    db: Session,
    vehicle_id: int,
    action_type: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    description: str | None = None,
    changed_by_id: int | None = None
) -> None:
    """Create a vehicle history entry"""
    history = VehicleHistory(
        vehicle_id=vehicle_id,
        changed_by_id=changed_by_id,
        action_type=action_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        description=description
    )
    db.add(history)
    db.flush()


def _format_value_for_history(value: Any) -> str:
    """Format a value for history display"""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    # Extract .value from SQLAlchemy/Python enums to avoid 'EnumClass.VALUE' repr
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


@router.get("/{item_id}/history")
def get_vehicle_history(item_id: int, db: Session = Depends(get_db)):
    """Get all history entries for a vehicle"""
    # Check if vehicle exists
    vehicle = db.get(Vehicle, item_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    
    # Query history with admin details
    history_entries = db.query(VehicleHistory).filter(
        VehicleHistory.vehicle_id == item_id
    ).order_by(VehicleHistory.changed_at.desc()).all()
    
    result = []
    for entry in history_entries:
        entry_dict = to_dict(entry)
        if entry.changed_by:
            entry_dict['changed_by_name'] = entry.changed_by.username
        else:
            entry_dict['changed_by_name'] = 'System'
        result.append(entry_dict)
    
    return result


@router.get("/{item_id}/files")
def get_vehicle_files(item_id: int, db: Session = Depends(get_db)):
    """Get all files for a vehicle"""
    vehicle = db.get(Vehicle, item_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    docs = db.query(VehicleDocument).filter(VehicleDocument.vehicle_id == item_id).all()
    result = []
    for doc in docs:
        url = None
        if doc.file_path:
            url = minio_client.get_presigned_url(
                minio_client.vehicle_documents_bucket, doc.file_path
            )
        d = to_dict(doc)
        d["url"] = url
        result.append(d)
    return result


@router.post("/{item_id}/files")
async def upload_vehicle_files(
    item_id: int,
    files: list[UploadFile] = File(...),
    document_type: str = "OTHER",
    db: Session = Depends(get_db),
):
    """Upload one or more files for a vehicle"""
    vehicle = db.get(Vehicle, item_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
    max_file_size = 20 * 1024 * 1024  # 20MB

    uploaded = []
    errors = []

    try:
        doc_type = DocumentTypeEnum(document_type)
    except ValueError:
        doc_type = DocumentTypeEnum.OTHER

    for file in files:
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in (file.filename or '') else ''
        if ext not in allowed_extensions:
            errors.append(f"{file.filename}: invalid type. Allowed: {', '.join(sorted(allowed_extensions))}")
            continue

        content = await file.read()
        if len(content) > max_file_size:
            errors.append(f"{file.filename}: too large (max 20MB)")
            continue
        await file.seek(0)

        object_name = minio_client.upload_document(file.file, file.filename, "vehicle-files", item_id)
        if not object_name:
            errors.append(f"{file.filename}: upload failed")
            continue

        doc = VehicleDocument(
            vehicle_id=item_id,
            type=doc_type,
            title=file.filename,
            file_path=object_name,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        d = to_dict(doc)
        d["url"] = minio_client.get_presigned_url(
            minio_client.vehicle_documents_bucket, object_name
        )
        uploaded.append(d)

    return {"uploaded": uploaded, "errors": errors}


@router.delete("/{item_id}/files/{file_id}")
def delete_vehicle_file(item_id: int, file_id: int, db: Session = Depends(get_db)):
    """Delete a vehicle file"""
    doc = db.query(VehicleDocument).filter(
        VehicleDocument.id == file_id,
        VehicleDocument.vehicle_id == item_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if doc.file_path:
        minio_client.delete_object(minio_client.vehicle_documents_bucket, doc.file_path)

    db.delete(doc)
    db.commit()
    return {"detail": "File deleted"}


def _get_rate_starting_prices(db: Session, vehicle_model_ids: list[int]) -> dict[int, float]:
    """Look up the shortest-duration rate tier price for each vehicle model.
    Returns a dict mapping vehicle_model_id -> price_per_day for the shortest tier.
    This is used as the 'From X/day' display price.
    """
    if not vehicle_model_ids:
        return {}
    from datetime import date
    today = date.today()
    # Find active rates valid today
    tiers = (
        db.query(RateTier)
        .join(Rate, RateTier.rate_id == Rate.id)
        .filter(
            and_(
                Rate.is_active == True,
                Rate.valid_from <= today,
                Rate.valid_until >= today,
                RateTier.vehicle_model_id.in_(vehicle_model_ids),
            )
        )
        .order_by(RateTier.from_days.asc())
        .all()
    )
    # For each model, pick the tier with the smallest from_days (shortest rental = "From" price)
    result: dict[int, float] = {}
    for tier in tiers:
        if tier.vehicle_model_id not in result:
            result[tier.vehicle_model_id] = float(tier.price_per_day)
    return result


@router.get("/", response_model=List[Dict[str, Any]])
def list_vehicles(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    available_only: bool = Query(False, description="Exclude vehicles that have an active DELIVERED booking"),
    vehicle_model_id: int = Query(None, description="Filter by vehicle model ID"),
):
    query = db.query(Vehicle).options(
        joinedload(Vehicle.location), 
        joinedload(Vehicle.photos),
        joinedload(Vehicle.vehicle_group),
        joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand),
        joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.photos),
        joinedload(Vehicle.bookings)
    )

    if available_only:
        # Subquery: vehicle IDs that have a booking with status DELIVERED
        from sqlalchemy import and_
        delivered_vehicle_ids = (
            db.query(Booking.vehicle_id)
            .filter(
                and_(
                    Booking.vehicle_id.isnot(None),
                    Booking.status == BookingStatusEnum.DELIVERED,
                )
            )
            .distinct()
            .subquery()
        )
        query = query.filter(Vehicle.id.notin_(delivered_vehicle_ids))

    if vehicle_model_id is not None:
        query = query.filter(Vehicle.vehicle_model_id == vehicle_model_id)

    items = query.offset(skip).limit(limit).all()

    # Pre-fetch rate-based starting prices for all vehicle models in this batch
    model_ids = list({item.vehicle_model_id for item in items if item.vehicle_model_id})
    rate_prices = _get_rate_starting_prices(db, model_ids)

    result = []
    for item in items:
        vehicle_dict = to_dict(item)
        # Compute status based on bookings
        active_bookings = [
            b for b in item.bookings 
            if b.status in (BookingStatusEnum.PENDING, BookingStatusEnum.CONFIRMED, BookingStatusEnum.DELIVERED)
        ]
        if active_bookings:
            # Get most recent active booking
            latest = max(active_bookings, key=lambda x: x.pickup_datetime)
            vehicle_dict['status'] = latest.status.value
        else:
            vehicle_dict['status'] = 'AVAILABLE'
        
        # Include active booking date ranges so frontend can check overlap with searched dates
        vehicle_dict['active_bookings'] = [
            {
                'pickup_datetime': b.pickup_datetime.isoformat() if b.pickup_datetime else None,
                'dropoff_datetime': b.dropoff_datetime.isoformat() if b.dropoff_datetime else None,
                'status': b.status.value,
            }
            for b in active_bookings
        ]
        
        if item.location:
            vehicle_dict['location_name'] = item.location.name
            vehicle_dict['location_full_name'] = f"{item.location.name}, {item.location.city}" if item.location.city else item.location.name
        else:
            vehicle_dict['location_name'] = None
            vehicle_dict['location_full_name'] = None
        
        # Add photos - use vehicle-specific photos if available, otherwise use model photos
        photos_to_use = item.photos if item.photos else (item.vehicle_model.photos if item.vehicle_model else [])
        if photos_to_use:
            vehicle_dict['photos'] = [
                {
                    'id': photo.id,
                    'url': get_photo_url(photo.object_name),
                    'object_name': photo.object_name,
                    'is_primary': photo.is_primary,
                    'display_order': photo.display_order,
                    'alt_text': photo.alt_text,
                    'source': 'vehicle' if photo.vehicle_id else 'model',
                }
                for photo in photos_to_use
            ]
        else:
            vehicle_dict['photos'] = []
        
        # Add brand and model information
        if item.vehicle_model:
            vehicle_dict['model_id'] = item.vehicle_model.id
            vehicle_dict['model_name'] = item.vehicle_model.name
            # For backward compatibility, also set make and model
            if item.vehicle_model.brand:
                vehicle_dict['brand_id'] = item.vehicle_model.brand.id
                vehicle_dict['brand_name'] = item.vehicle_model.brand.name
                vehicle_dict['make'] = item.vehicle_model.brand.name
            else:
                vehicle_dict['make'] = ''
            vehicle_dict['model'] = item.vehicle_model.name
        else:
            # Fallback for vehicles without vehicle_model
            vehicle_dict['make'] = item.make or ''
            vehicle_dict['model'] = item.model or ''
        
        # Add vehicle group pricing information
        if item.vehicle_group:
            vehicle_dict['vehicle_group_name'] = item.vehicle_group.name
            vehicle_dict['vehicle_group_id'] = item.vehicle_group.id

        # Resolve starting_price: rate tier > vehicle group base > DB value
        if item.vehicle_model_id and item.vehicle_model_id in rate_prices:
            vehicle_dict['starting_price'] = rate_prices[item.vehicle_model_id]
        elif item.vehicle_group and item.vehicle_group.base_price_per_day is not None:
            if item.starting_price is None or item.starting_price == 50.00:
                vehicle_dict['starting_price'] = float(item.vehicle_group.base_price_per_day)
        
        result.append(vehicle_dict)
    return result


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_vehicle(item_id: int, db: Session = Depends(get_db)):
    obj = db.query(Vehicle).options(
        joinedload(Vehicle.location), 
        joinedload(Vehicle.photos),
        joinedload(Vehicle.vehicle_group),
        joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.photos),
        joinedload(Vehicle.vehicle_model).joinedload(VehicleModel.brand),
        joinedload(Vehicle.bookings)
    ).filter(Vehicle.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    vehicle_dict = to_dict(obj)
    # Compute status based on bookings
    active_bookings = [
        b for b in obj.bookings 
        if b.status in (BookingStatusEnum.PENDING, BookingStatusEnum.CONFIRMED, BookingStatusEnum.DELIVERED)
    ]
    if active_bookings:
        # Get most recent active booking
        latest = max(active_bookings, key=lambda x: x.pickup_datetime)
        vehicle_dict['status'] = latest.status.value
    else:
        vehicle_dict['status'] = 'AVAILABLE'
    
    if obj.location:
        vehicle_dict['location_name'] = obj.location.name
        vehicle_dict['location_full_name'] = f"{obj.location.name}, {obj.location.city}" if obj.location.city else obj.location.name
    else:
        vehicle_dict['location_name'] = None
        vehicle_dict['location_full_name'] = None
    
    # Add photos - use vehicle-specific photos if available, otherwise use model photos
    photos_to_use = obj.photos if obj.photos else (obj.vehicle_model.photos if obj.vehicle_model else [])
    if photos_to_use:
        vehicle_dict['photos'] = [
            {
                'id': photo.id,
                'url': get_photo_url(photo.object_name),
                'object_name': photo.object_name,
                'is_primary': photo.is_primary,
                'display_order': photo.display_order,
                'alt_text': photo.alt_text,
                'source': 'vehicle' if photo.vehicle_id else 'model'  # Indicate photo source
            }
            for photo in photos_to_use
        ]
    else:
        vehicle_dict['photos'] = []
    
    # Add brand and model information
    if obj.vehicle_model:
        vehicle_dict['model_id'] = obj.vehicle_model.id
        vehicle_dict['model_name'] = obj.vehicle_model.name
        # Override legacy make/model with VehicleModel data (same as list endpoint)
        if obj.vehicle_model.brand:
            vehicle_dict['brand_id'] = obj.vehicle_model.brand.id
            vehicle_dict['brand_name'] = obj.vehicle_model.brand.name
            vehicle_dict['make'] = obj.vehicle_model.brand.name
        else:
            vehicle_dict['make'] = obj.make or ''
        vehicle_dict['model'] = obj.vehicle_model.name
        # Add suitcase/bag info from vehicle model
        if obj.vehicle_model.large_suitcases is not None:
            vehicle_dict['large_suitcases'] = obj.vehicle_model.large_suitcases
        if obj.vehicle_model.small_suitcases is not None:
            vehicle_dict['small_suitcases'] = obj.vehicle_model.small_suitcases
    else:
        # Fallback for vehicles without vehicle_model
        vehicle_dict['make'] = obj.make or ''
        vehicle_dict['model'] = obj.model or ''
    
    # Add vehicle group pricing information and features
    if obj.vehicle_group:
        vehicle_dict['vehicle_group_name'] = obj.vehicle_group.name
        vehicle_dict['vehicle_group_id'] = obj.vehicle_group.id
        # Include vehicle group features
        if obj.vehicle_group.features:
            vehicle_dict['features'] = [f.strip() for f in obj.vehicle_group.features.split(',') if f.strip()]
        # Include vehicle group description as fallback (Vehicle model doesn't have description)
        if obj.vehicle_group.description:
            vehicle_dict['description'] = obj.vehicle_group.description

    # Resolve starting_price: rate tier > vehicle group base > DB value
    if obj.vehicle_model_id:
        rate_prices = _get_rate_starting_prices(db, [obj.vehicle_model_id])
        if obj.vehicle_model_id in rate_prices:
            vehicle_dict['starting_price'] = rate_prices[obj.vehicle_model_id]
        elif obj.vehicle_group and obj.vehicle_group.base_price_per_day is not None:
            if obj.starting_price is None or obj.starting_price == 50.00:
                vehicle_dict['starting_price'] = float(obj.vehicle_group.base_price_per_day)
    elif obj.vehicle_group and obj.vehicle_group.base_price_per_day is not None:
        if obj.starting_price is None or obj.starting_price == 50.00:
            vehicle_dict['starting_price'] = float(obj.vehicle_group.base_price_per_day)
    
    return vehicle_dict


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_vehicle(payload: Dict[str, Any], db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    obj = Vehicle()
    apply_updates(obj, payload)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    
    # Create initial history entry
    description = f"Vehicle created: {obj.license_plate}"
    if obj.vehicle_model:
        description += f" ({obj.brand_name} {obj.model_name})"
    elif obj.make and obj.model:
        description += f" ({obj.make} {obj.model})"
    
    _create_history_entry(
        db=db,
        vehicle_id=obj.id,
        action_type="CREATED",
        description=description,
        changed_by_id=getattr(admin, 'id', None)
    )
    db.commit()
    
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_vehicle(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    obj = db.get(Vehicle, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    # Strip computed/booking-derived status values that are not valid VehicleStatusEnum values.
    # The GET endpoint returns a computed status from active bookings (PENDING, CONFIRMED, DELIVERED)
    # which are booking statuses, not vehicle statuses. If such a value is sent back we must ignore it.
    valid_vehicle_statuses = {e.value for e in VehicleStatusEnum}
    payload = dict(payload)  # work on a copy
    if 'status' in payload:
        status_val = str(payload['status']).upper() if payload['status'] else ''
        if status_val not in valid_vehicle_statuses:
            payload.pop('status')

    # Track changes for history
    changes = []
    tracked_fields = {
        'status': 'Status',
        'location_id': 'Location',
        'mileage': 'Mileage',
        'vehicle_model_id': 'Model',
        'vehicle_group_id': 'Vehicle Group',
        'year': 'Year',
        'color': 'Color',
        'license_plate': 'License Plate',
        'fuel_type': 'Fuel Type',
        'transmission': 'Transmission',
        'seats': 'Seats',
        'doors': 'Doors',
        'vin': 'VIN'
    }
    
    for field, label in tracked_fields.items():
        if field in payload:
            old_val = getattr(obj, field, None)
            new_val = payload[field]
            if old_val != new_val:
                old_val_formatted = _format_value_for_history(old_val)
                new_val_formatted = _format_value_for_history(new_val)
                changes.append({
                    'field': field,
                    'label': label,
                    'old': old_val_formatted,
                    'new': new_val_formatted
                })
    
    apply_updates(obj, payload)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(obj)
    
    # Create history entries for each change
    for change in changes:
        _create_history_entry(
            db=db,
            vehicle_id=obj.id,
            action_type=f"{change['field'].upper()}_CHANGED",
            field_name=change['field'],
            old_value=change['old'],
            new_value=change['new'],
            description=f"{change['label']} changed from {change['old']} to {change['new']}",
            changed_by_id=getattr(admin, 'id', None)
        )
    
    if changes:
        db.commit()
    
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
