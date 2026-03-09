"""
API routes for managing vehicle brands
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Brand, Admin
from app.core.auth import get_optional_admin
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/admin/brands", tags=["brands"])


@router.get("", response_model=List[Dict[str, Any]])
def list_brands(
    db: Session = Depends(get_db),
    search: str = None
):
    """List all vehicle brands"""
    query = db.query(Brand)
    
    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))
    
    query = query.order_by(Brand.name)
    brands = query.all()
    return [to_dict(brand) for brand in brands]


@router.get("/{brand_id}", response_model=Dict[str, Any])
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    """Get a specific brand"""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return to_dict(brand)


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_brand(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Create a new brand"""
    # Check if brand with same name already exists
    existing = db.query(Brand).filter(Brand.name == payload.get('name')).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand '{payload.get('name')}' already exists"
        )
    
    brand = Brand(**payload)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return to_dict(brand)


@router.put("/{brand_id}", response_model=Dict[str, Any])
def update_brand(
    brand_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Update a brand"""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    # Check if changing name would conflict
    if 'name' in payload and payload['name'] != brand.name:
        existing = db.query(Brand).filter(Brand.name == payload['name']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand '{payload['name']}' already exists"
            )
    
    apply_updates(brand, payload)
    db.commit()
    db.refresh(brand)
    return to_dict(brand)


@router.patch("/{brand_id}", response_model=Dict[str, Any])
def partial_update_brand(
    brand_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Partially update a brand"""
    return update_brand(brand_id, payload, db, current_admin)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Delete a brand (will cascade delete all associated models and update vehicles)"""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    db.delete(brand)
    db.commit()
    return None
