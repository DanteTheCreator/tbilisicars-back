from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.core.db import get_db
from app.core.minio import minio_client
from app.models.vehicle import Vehicle
from app.models.vehicle_model import VehicleModel
from app.models.vehicle_photo import VehiclePhoto

router = APIRouter()


def get_photo_url(object_name: str) -> str:
    """Generate public URL for a photo stored in MinIO via nginx proxy."""
    base_url = os.getenv('PHOTO_BASE_URL', 'https://tbilisicars.live')
    bucket = os.getenv('MINIO_VEHICLE_PHOTOS_BUCKET', 'vehicle-photos')
    return f"{base_url}/{bucket}/{object_name}"

@router.post("/vehicles/{vehicle_id}/photos")
async def upload_vehicle_photos(
    vehicle_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload one or more photos for a vehicle
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Validate file types
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    max_file_size = 10 * 1024 * 1024  # 10MB
    
    uploaded_photos = []
    errors = []
    
    for file in files:
        try:
            # Validate file extension
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                errors.append(f"File {file.filename}: Invalid file type. Allowed: {', '.join(allowed_extensions)}")
                continue
            
            # Validate file size
            content = await file.read()
            file_size = len(content)
            if file_size > max_file_size:
                errors.append(f"File {file.filename}: File too large. Maximum size: 10MB")
                continue
            
            # Reset file pointer
            await file.seek(0)
            
            # Upload to MinIO
            object_name = minio_client.upload_vehicle_photo(file.file, file.filename, vehicle_id)
            
            if object_name:
                # Save photo metadata to database
                photo_record = VehiclePhoto(
                    vehicle_id=vehicle_id,
                    object_name=object_name,
                    original_filename=file.filename,
                    file_size=file_size,
                    content_type=file.content_type or f"image/{file_extension}",
                    display_order=0  # Can be updated later for ordering
                )
                
                db.add(photo_record)
                db.commit()
                db.refresh(photo_record)
                
                # Get the public URL
                photo_url = get_photo_url(object_name)
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
            # Rollback any partial database changes
            db.rollback()
    
    return JSONResponse(content={
        "message": f"Processed {len(files)} files",
        "uploaded": uploaded_photos,
        "errors": errors,
        "total_uploaded": len(uploaded_photos),
        "total_errors": len(errors)
    })

@router.get("/vehicles/{vehicle_id}/photos")
async def get_vehicle_photos(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all photos for a vehicle from database with MinIO URLs
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Get photos from database (ordered by display_order)
    photo_records = db.query(VehiclePhoto).filter(
        VehiclePhoto.vehicle_id == vehicle_id
    ).order_by(VehiclePhoto.display_order, VehiclePhoto.created_at).all()
    
    photos = []
    for photo_record in photo_records:
        # Get current URL for the photo via nginx proxy
        photo_url = get_photo_url(photo_record.object_name)
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
        "vehicle_id": vehicle_id,
        "photos": photos,
        "total_photos": len(photos)
    })

@router.delete("/vehicles/{vehicle_id}/photos/{object_name:path}")
async def delete_vehicle_photo(
    vehicle_id: int,
    object_name: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific vehicle photo from both MinIO and database
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Find the photo record in database
    photo_record = db.query(VehiclePhoto).filter(
        VehiclePhoto.vehicle_id == vehicle_id,
        VehiclePhoto.object_name == object_name
    ).first()
    
    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    try:
        # Delete from MinIO first
        minio_success = minio_client.delete_vehicle_photo(object_name)
        
        if minio_success:
            # Delete from database
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

@router.put("/vehicles/{vehicle_id}/photos/{photo_id}/primary")
async def set_primary_photo(
    vehicle_id: int,
    photo_id: int,
    db: Session = Depends(get_db)
):
    """
    Set a photo as the primary photo for a vehicle
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Find the photo record
    photo_record = db.query(VehiclePhoto).filter(
        VehiclePhoto.id == photo_id,
        VehiclePhoto.vehicle_id == vehicle_id
    ).first()
    
    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    try:
        # Remove primary flag from all other photos for this vehicle
        db.query(VehiclePhoto).filter(
            VehiclePhoto.vehicle_id == vehicle_id,
            VehiclePhoto.id != photo_id
        ).update({"is_primary": False})
        
        # Set this photo as primary
        photo_record.is_primary = True
        db.commit()
        
        return JSONResponse(content={
            "message": "Primary photo updated successfully",
            "photo_id": photo_id
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update primary photo: {str(e)}")

@router.put("/vehicles/{vehicle_id}/photos/reorder")
async def reorder_photos(
    vehicle_id: int,
    photo_orders: List[dict],  # [{"photo_id": 1, "display_order": 0}, ...]
    db: Session = Depends(get_db)
):
    """
    Reorder photos for a vehicle
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    try:
        for order_data in photo_orders:
            photo_id = order_data.get("photo_id")
            display_order = order_data.get("display_order")
            
            if photo_id is None or display_order is None:
                continue
                
            # Update display order
            db.query(VehiclePhoto).filter(
                VehiclePhoto.id == photo_id,
                VehiclePhoto.vehicle_id == vehicle_id
            ).update({"display_order": display_order})
        
        db.commit()
        
        return JSONResponse(content={
            "message": "Photo order updated successfully",
            "updated_photos": len(photo_orders)
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reorder photos: {str(e)}")


# ==================== VEHICLE MODEL PHOTO ROUTES ====================

@router.post("/vehicle-models/{model_id}/photos")
async def upload_model_photos(
    model_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload one or more photos for a vehicle model
    These photos will be shared by all vehicles of this model
    """
    # Check if model exists
    model = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    
    # Validate file types
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    max_file_size = 10 * 1024 * 1024  # 10MB
    
    uploaded_photos = []
    errors = []
    
    for file in files:
        try:
            # Validate file extension
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                errors.append(f"File {file.filename}: Invalid file type. Allowed: {', '.join(allowed_extensions)}")
                continue
            
            # Validate file size
            content = await file.read()
            file_size = len(content)
            if file_size > max_file_size:
                errors.append(f"File {file.filename}: File too large. Maximum size: 10MB")
                continue
            
            # Reset file pointer
            await file.seek(0)

            # Upload to MinIO using proper method (UUID filename, image optimization)
            object_name = minio_client.upload_model_photo(file.file, file.filename, model_id)

            if object_name:
                # Save photo metadata to database
                photo_record = VehiclePhoto(
                    vehicle_model_id=model_id,
                    object_name=object_name,
                    original_filename=file.filename,
                    file_size=file_size,
                    content_type=file.content_type or f"image/{file_extension}",
                    display_order=0
                )
                
                db.add(photo_record)
                db.commit()
                db.refresh(photo_record)
                
                # Get the public URL
                photo_url = get_photo_url(object_name)
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
    
    status_code = 200
    if len(uploaded_photos) == 0 and len(errors) > 0:
        status_code = 422

    return JSONResponse(
        status_code=status_code,
        content={
            "message": f"Processed {len(files)} files",
            "uploaded": uploaded_photos,
            "errors": errors,
            "total_uploaded": len(uploaded_photos),
            "total_errors": len(errors)
        }
    )


@router.delete("/vehicle-models/{model_id}/photos/{photo_id}")
async def delete_model_photo(
    model_id: int,
    photo_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a specific vehicle model photo from both MinIO and database
    """
    model = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")

    photo_record = db.query(VehiclePhoto).filter(
        VehiclePhoto.id == photo_id,
        VehiclePhoto.vehicle_model_id == model_id
    ).first()

    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        minio_success = minio_client.delete_vehicle_photo(photo_record.object_name)

        if minio_success:
            db.delete(photo_record)
            db.commit()
            return JSONResponse(content={
                "message": "Photo deleted successfully",
                "photo_id": photo_id
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to delete photo from storage")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")


@router.get("/vehicle-models/{model_id}/photos")
async def get_model_photos(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all photos for a vehicle model
    """
    # Check if model exists
    model = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    
    # Get photos from database
    photo_records = db.query(VehiclePhoto).filter(
        VehiclePhoto.vehicle_model_id == model_id
    ).order_by(VehiclePhoto.display_order, VehiclePhoto.created_at).all()
    
    photos = []
    for photo_record in photo_records:
        photo_url = get_photo_url(photo_record.object_name)
        if photo_url:
            photos.append({
                "id": photo_record.id,
                "filename": photo_record.original_filename,
                "object_name": photo_record.object_name,
                "url": photo_url,
                "file_size": photo_record.file_size,
                "content_type": photo_record.content_type,
                "is_primary": photo_record.is_primary,
                "display_order": photo_record.display_order,
                "created_at": photo_record.created_at.isoformat()
            })
    
    return JSONResponse(content={"photos": photos, "count": len(photos)})


@router.post("/upload-test")
async def test_upload(file: UploadFile = File(...)):
    """
    Test endpoint for file upload functionality
    """
    try:
        content = await file.read()
        return JSONResponse(content={
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "message": "File received successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
