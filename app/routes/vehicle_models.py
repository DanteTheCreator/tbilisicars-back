"""
API routes for managing vehicle models
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models import VehicleModel, Brand, Admin, VehicleGroup
from app.core.auth import get_optional_admin
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/admin/vehicle-models", tags=["vehicle-models"])


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Get all categories from vehicle groups"""
    result = db.query(VehicleGroup.category).filter(
        VehicleGroup.category.isnot(None),
        VehicleGroup.category != ''
    ).distinct().order_by(VehicleGroup.category).all()
    
    return [category[0] for category in result if category[0]]


@router.get("", response_model=List[Dict[str, Any]])
def list_vehicle_models(
    db: Session = Depends(get_db),
    brand_id: int = None,
    active_only: bool = True,
    search: str = None
):
    """List all vehicle models"""
    query = db.query(VehicleModel).options(joinedload(VehicleModel.brand))
    
    if brand_id:
        query = query.filter(VehicleModel.brand_id == brand_id)
    
    if active_only:
        query = query.filter(VehicleModel.active == True)
    
    if search:
        query = query.filter(
            or_(
                VehicleModel.name.ilike(f"%{search}%"),
                VehicleModel.description.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(VehicleModel.name)
    models = query.all()
    
    result = []
    for model in models:
        model_dict = to_dict(model)
        if model.brand:
            model_dict['brand'] = to_dict(model.brand)
        result.append(model_dict)
    
    return result


@router.get("/{model_id}", response_model=Dict[str, Any])
def get_vehicle_model(model_id: int, db: Session = Depends(get_db)):
    """Get a specific vehicle model"""
    model = db.query(VehicleModel).options(joinedload(VehicleModel.brand)).filter(VehicleModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle model not found")
    
    model_dict = to_dict(model)
    if model.brand:
        model_dict['brand'] = to_dict(model.brand)
    
    return model_dict


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_vehicle_model(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Create a new vehicle model"""
    # Verify brand exists
    brand = db.get(Brand, payload.get('brand_id'))
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {payload.get('brand_id')} not found"
        )
    
    # Check if model with same name already exists for this brand
    existing = db.query(VehicleModel).filter(
        VehicleModel.brand_id == payload.get('brand_id'),
        VehicleModel.name == payload.get('name')
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{payload.get('name')}' already exists for brand '{brand.name}'"
        )
    
    model = VehicleModel(**payload)
    db.add(model)
    db.commit()
    db.refresh(model)
    
    model_dict = to_dict(model)
    model_dict['brand'] = to_dict(brand)
    return model_dict


@router.put("/{model_id}", response_model=Dict[str, Any])
def update_vehicle_model(
    model_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Update a vehicle model"""
    model = db.query(VehicleModel).options(joinedload(VehicleModel.brand)).filter(VehicleModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle model not found")
    
    # If changing brand_id, verify it exists
    if 'brand_id' in payload and payload['brand_id'] != model.brand_id:
        brand = db.get(Brand, payload['brand_id'])
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with id {payload['brand_id']} not found"
            )
    
    # Check if changing name would conflict
    if 'name' in payload or 'brand_id' in payload:
        new_name = payload.get('name', model.name)
        new_brand_id = payload.get('brand_id', model.brand_id)
        
        existing = db.query(VehicleModel).filter(
            VehicleModel.brand_id == new_brand_id,
            VehicleModel.name == new_name,
            VehicleModel.id != model_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{new_name}' already exists for this brand"
            )
    
    apply_updates(model, payload)
    db.commit()
    db.refresh(model)
    
    model_dict = to_dict(model)
    if model.brand:
        model_dict['brand'] = to_dict(model.brand)
    
    return model_dict


@router.patch("/{model_id}", response_model=Dict[str, Any])
def partial_update_vehicle_model(
    model_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Partially update a vehicle model"""
    return update_vehicle_model(model_id, payload, db, current_admin)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_optional_admin)
):
    """Delete a vehicle model (will cascade delete all associated vehicles)"""
    model = db.get(VehicleModel, model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle model not found")
    
    db.delete(model)
    db.commit()
    return None
