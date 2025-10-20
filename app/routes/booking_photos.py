from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.db import get_db
from app.core.minio import minio_client
from app.models.booking import Booking
from app.models.booking_photo import BookingPhoto

router = APIRouter()

@router.post("/bookings/{booking_id}/photos")
async def upload_booking_photos(
    booking_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # Check if booking exists
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    max_file_size = 10 * 1024 * 1024  # 10MB

    uploaded_photos = []
    errors = []

    for file in files:
        try:
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                errors.append(f"File {file.filename}: Invalid file type. Allowed: {', '.join(allowed_extensions)}")
                continue

            content = await file.read()
            file_size = len(content)
            if file_size > max_file_size:
                errors.append(f"File {file.filename}: File too large. Maximum size: 10MB")
                continue

            await file.seek(0)

            # Upload to MinIO using vehicle_photos bucket (reusing bucket for now)
            object_name = minio_client.upload_vehicle_photo(file.file, file.filename, booking_id)

            if object_name:
                photo_record = BookingPhoto(
                    booking_id=booking_id,
                    object_name=object_name,
                    original_filename=file.filename,
                    file_size=file_size,
                    content_type=file.content_type or f"image/{file_extension}",
                    display_order=0
                )
                db.add(photo_record)
                db.commit()
                db.refresh(photo_record)

                photo_url = minio_client.get_vehicle_photo_url(object_name)
                uploaded_photos.append({
                    "id": photo_record.id,
                    "filename": file.filename,
                    "object_name": object_name,
                    "url": photo_url,
                    "file_size": file_size,
                    "content_type": photo_record.content_type,
                    "created_at": photo_record.created_at.isoformat()
                })
            else:
                errors.append(f"File {file.filename}: Failed to upload to storage")
        except Exception as e:
            errors.append(f"File {file.filename}: {str(e)}")
            db.rollback()

    return JSONResponse(content={
        "message": f"Processed {len(files)} files",
        "uploaded": uploaded_photos,
        "errors": errors,
        "total_uploaded": len(uploaded_photos),
        "total_errors": len(errors)
    })


@router.get("/bookings/{booking_id}/photos")
async def get_booking_photos(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    photo_records = db.query(BookingPhoto).filter(
        BookingPhoto.booking_id == booking_id
    ).order_by(BookingPhoto.display_order, BookingPhoto.created_at).all()

    photos = []
    for photo_record in photo_records:
        photo_url = minio_client.get_vehicle_photo_url(photo_record.object_name)
        if photo_url:
            photos.append({
                "id": photo_record.id,
                "object_name": photo_record.object_name,
                "url": photo_url,
                "filename": photo_record.original_filename,
                "file_size": photo_record.file_size,
                "content_type": photo_record.content_type,
                "is_primary": photo_record.is_primary,
                "display_order": photo_record.display_order,
                "alt_text": photo_record.alt_text,
                "created_at": photo_record.created_at.isoformat(),
                "updated_at": photo_record.updated_at.isoformat()
            })

    return JSONResponse(content={
        "booking_id": booking_id,
        "photos": photos,
        "total_photos": len(photos)
    })


@router.delete("/bookings/{booking_id}/photos/{object_name:path}")
async def delete_booking_photo(
    booking_id: int,
    object_name: str,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    photo_record = db.query(BookingPhoto).filter(
        BookingPhoto.booking_id == booking_id,
        BookingPhoto.object_name == object_name
    ).first()

    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        minio_success = minio_client.delete_vehicle_photo(object_name)
        if minio_success:
            db.delete(photo_record)
            db.commit()
            return JSONResponse(content={
                "message": "Photo deleted successfully",
                "object_name": object_name,
                "photo_id": photo_record.id
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to delete photo from storage")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")


@router.put("/bookings/{booking_id}/photos/{photo_id}/primary")
async def set_primary_photo(
    booking_id: int,
    photo_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    photo_record = db.query(BookingPhoto).filter(
        BookingPhoto.id == photo_id,
        BookingPhoto.booking_id == booking_id
    ).first()

    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        db.query(BookingPhoto).filter(
            BookingPhoto.booking_id == booking_id,
            BookingPhoto.id != photo_id
        ).update({"is_primary": False})

        photo_record.is_primary = True
        db.commit()

        return JSONResponse(content={
            "message": "Primary photo updated successfully",
            "photo_id": photo_id
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update primary photo: {str(e)}")


@router.put("/bookings/{booking_id}/photos/reorder")
async def reorder_photos(
    booking_id: int,
    photo_orders: List[dict],
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        for order_data in photo_orders:
            photo_id = order_data.get("photo_id")
            display_order = order_data.get("display_order")

            if photo_id is None or display_order is None:
                continue

            db.query(BookingPhoto).filter(
                BookingPhoto.id == photo_id,
                BookingPhoto.booking_id == booking_id
            ).update({"display_order": display_order})

        db.commit()

        return JSONResponse(content={
            "message": "Photo order updated successfully",
            "updated_photos": len(photo_orders)
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reorder photos: {str(e)}")
