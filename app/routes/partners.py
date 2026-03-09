"""
API routes for managing partners/brokers
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import os
import uuid
from pathlib import Path

from app.models import Partner, PartnerDocument, Vehicle, Admin
from app.core.auth import get_optional_admin
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/admin/partners", tags=["partners"])

# Configure upload directory
UPLOAD_DIR = Path("/app/uploads/partner_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=List[Dict[str, Any]])
def list_partners(
    db: Session = Depends(get_db),
    search: str = None
):
    """List all partners"""
    query = db.query(Partner).options(
        joinedload(Partner.vehicles),
        joinedload(Partner.documents)
    )
    
    if search:
        query = query.filter(
            or_(
                Partner.name.ilike(f"%{search}%"),
                Partner.contact_email.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(Partner.name)
    partners = query.all()
    
    result = []
    for partner in partners:
        partner_dict = to_dict(partner)
        partner_dict['vehicle_count'] = len(partner.vehicles)
        partner_dict['document_count'] = len(partner.documents)
        partner_dict['vehicles'] = [{'id': v.id, 'license_plate': v.license_plate} for v in partner.vehicles]
        partner_dict['documents'] = [to_dict(d) for d in partner.documents]
        result.append(partner_dict)
    
    return result


@router.get("/{partner_id}", response_model=Dict[str, Any])
def get_partner(partner_id: int, db: Session = Depends(get_db)):
    """Get a specific partner with all details"""
    partner = db.query(Partner).options(
        joinedload(Partner.vehicles),
        joinedload(Partner.documents),
        joinedload(Partner.bookings)
    ).filter(Partner.id == partner_id).first()
    
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    partner_dict = to_dict(partner)
    partner_dict['vehicles'] = [
        {
            'id': v.id,
            'license_plate': v.license_plate,
            'make': v.brand_name,
            'model': v.model_name,
            'year': v.year
        } for v in partner.vehicles
    ]
    partner_dict['documents'] = [to_dict(d) for d in partner.documents]
    partner_dict['booking_count'] = len(partner.bookings)
    
    return partner_dict


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_partner(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Create a new partner"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[PARTNER] Received payload: {payload}")
        
        # Check if partner with same name already exists
        existing = db.query(Partner).filter(Partner.name == payload.get('name')).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partner with this name already exists"
            )
        
        # Extract vehicle IDs if provided
        vehicle_ids = payload.pop('vehicle_ids', [])
        
        # Clean empty strings to None for nullable fields
        if 'contact_email' in payload and not payload['contact_email']:
            payload['contact_email'] = None
        if 'contact_number' in payload and not payload['contact_number']:
            payload['contact_number'] = None
        
        logger.info(f"[PARTNER] Creating partner with data: {payload}")
        partner = Partner(**payload)
        
        # Associate vehicles if provided
        if vehicle_ids:
            vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
            partner.vehicles = vehicles
        
        db.add(partner)
        db.commit()
        db.refresh(partner)
        
        logger.info(f"[PARTNER] Successfully created partner ID: {partner.id}")
        return to_dict(partner)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[PARTNER] Error creating partner: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create partner: {str(e)}"
        )


@router.put("/{partner_id}", response_model=Dict[str, Any])
def update_partner(
    partner_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Update a partner"""
    partner = db.get(Partner, partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    # Check for name uniqueness if name is being changed
    if 'name' in payload and payload['name'] != partner.name:
        existing = db.query(Partner).filter(Partner.name == payload['name']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partner with this name already exists"
            )
    
    # Handle vehicle associations separately
    if 'vehicle_ids' in payload:
        vehicle_ids = payload.pop('vehicle_ids')
        vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
        partner.vehicles = vehicles
    
    apply_updates(partner, payload)
    db.commit()
    db.refresh(partner)
    
    return to_dict(partner)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Delete a partner"""
    partner = db.get(Partner, partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    # Delete associated documents from filesystem
    for doc in partner.documents:
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting file {doc.file_path}: {e}")
    
    db.delete(partner)
    db.commit()
    return None


@router.post("/{partner_id}/documents", response_model=Dict[str, Any])
async def upload_partner_document(
    partner_id: int,
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Upload a document for a partner"""
    partner = db.get(Partner, partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create document record
    document = PartnerDocument(
        partner_id=partner_id,
        title=title,
        file_path=str(file_path)
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return to_dict(document)


@router.get("/{partner_id}/documents/{document_id}/download")
def download_partner_document(
    partner_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Download a partner document"""
    document = db.query(PartnerDocument).filter(
        PartnerDocument.id == document_id,
        PartnerDocument.partner_id == partner_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    file_path = Path(document.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    
    # Get original filename from title and file extension
    file_extension = file_path.suffix
    filename = f"{document.title}{file_extension}"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


@router.delete("/{partner_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_document(
    partner_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Delete a partner document"""
    document = db.query(PartnerDocument).filter(
        PartnerDocument.id == document_id,
        PartnerDocument.partner_id == partner_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    # Delete file from filesystem
    try:
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Error deleting file {document.file_path}: {e}")
    
    db.delete(document)
    db.commit()
    return None


@router.get("/{partner_id}/vehicles", response_model=List[Dict[str, Any]])
def get_partner_vehicles(partner_id: int, db: Session = Depends(get_db)):
    """Get all vehicles associated with a partner"""
    partner = db.query(Partner).options(joinedload(Partner.vehicles)).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    return [
        {
            'id': v.id,
            'license_plate': v.license_plate,
            'make': v.brand_name,
            'model': v.model_name,
            'year': v.year,
            'status': v.status
        } for v in partner.vehicles
    ]


@router.post("/{partner_id}/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_vehicle_to_partner(
    partner_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Associate a vehicle with a partner"""
    partner = db.get(Partner, partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    
    if vehicle not in partner.vehicles:
        partner.vehicles.append(vehicle)
        db.commit()
    
    return None


@router.delete("/{partner_id}/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_vehicle_from_partner(
    partner_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Remove a vehicle association from a partner"""
    partner = db.get(Partner, partner_id)
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    
    if vehicle in partner.vehicles:
        partner.vehicles.remove(vehicle)
        db.commit()
    
    return None
