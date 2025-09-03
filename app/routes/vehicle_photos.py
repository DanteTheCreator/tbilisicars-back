from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.core.db import get_db
from app.core.minio import minio_client
from app.models.vehicle import Vehicle

router = APIRouter()

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
            if len(content) > max_file_size:
                errors.append(f"File {file.filename}: File too large. Maximum size: 10MB")
                continue
            
            # Reset file pointer
            await file.seek(0)
            
            # Upload to MinIO
            object_name = minio_client.upload_vehicle_photo(file.file, file.filename, vehicle_id)
            
            if object_name:
                # Get the public URL
                photo_url = minio_client.get_vehicle_photo_url(object_name)
                uploaded_photos.append({
                    "filename": file.filename,
                    "object_name": object_name,
                    "url": photo_url
                })
            else:
                errors.append(f"File {file.filename}: Failed to upload")
                
        except Exception as e:
            errors.append(f"File {file.filename}: {str(e)}")
    
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
    Get all photos for a vehicle
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Get photos from MinIO
    photo_objects = minio_client.list_vehicle_photos(vehicle_id)
    
    photos = []
    for object_name in photo_objects:
        photo_url = minio_client.get_vehicle_photo_url(object_name)
        if photo_url:
            photos.append({
                "object_name": object_name,
                "url": photo_url,
                "filename": object_name.split('/')[-1]
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
    Delete a specific vehicle photo
    """
    # Check if vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Validate that the object belongs to this vehicle
    if not object_name.startswith(f"vehicles/{vehicle_id}/"):
        raise HTTPException(status_code=403, detail="Access denied to this photo")
    
    # Delete from MinIO
    success = minio_client.delete_vehicle_photo(object_name)
    
    if success:
        return JSONResponse(content={
            "message": "Photo deleted successfully",
            "object_name": object_name
        })
    else:
        raise HTTPException(status_code=500, detail="Failed to delete photo")

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
