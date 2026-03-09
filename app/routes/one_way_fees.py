from __future__ import annotations

from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_super_admin
from app.core.db import get_db
from app.models.one_way_fee import OneWayFee
from app.models.location import Location
from app.models.admin import Admin

router = APIRouter(prefix="/admin/one-way-fees", tags=["One-Way Fees"])


class OneWayFeeResponse(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    from_location_name: str
    to_location_name: str
    fee_amount: float
    currency: str
    is_active: bool
    created_at: str


class CreateOneWayFeeRequest(BaseModel):
    from_location_id: int
    to_location_id: int
    fee_amount: float
    currency: str = "EUR"
    is_active: bool = True


class UpdateOneWayFeeRequest(BaseModel):
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    fee_amount: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


def fee_to_response(fee: OneWayFee) -> OneWayFeeResponse:
    """Convert OneWayFee model to response."""
    from_name = fee.from_location.name if fee.from_location else f"Location #{fee.from_location_id}"
    to_name = fee.to_location.name if fee.to_location else f"Location #{fee.to_location_id}"
    return OneWayFeeResponse(
        id=fee.id,
        from_location_id=fee.from_location_id,
        to_location_id=fee.to_location_id,
        from_location_name=from_name,
        to_location_name=to_name,
        fee_amount=float(fee.fee_amount),
        currency=fee.currency,
        is_active=fee.is_active,
        created_at=fee.created_at.isoformat()
    )


@router.get("", response_model=List[OneWayFeeResponse])
async def list_one_way_fees(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of all one-way fees."""
    fees = db.query(OneWayFee).all()
    return [fee_to_response(fee) for fee in fees]


@router.get("/active", response_model=List[OneWayFeeResponse])
async def list_active_one_way_fees(
    db: Session = Depends(get_db)
):
    """Get list of active one-way fees (public endpoint)."""
    fees = db.query(OneWayFee).filter(OneWayFee.is_active == True).all()
    return [fee_to_response(fee) for fee in fees]


@router.get("/calculate")
async def calculate_one_way_fee(
    from_location_id: int,
    to_location_id: int,
    db: Session = Depends(get_db)
):
    """Calculate one-way fee for given locations."""
    if from_location_id == to_location_id:
        return {"fee_amount": 0.0, "currency": "EUR", "applies": False}
    
    fee = db.query(OneWayFee).filter(
        OneWayFee.from_location_id == from_location_id,
        OneWayFee.to_location_id == to_location_id,
        OneWayFee.is_active == True
    ).first()
    
    if fee:
        return {
            "fee_amount": float(fee.fee_amount),
            "currency": fee.currency,
            "applies": True,
            "from_location": fee.from_location.name if fee.from_location else None,
            "to_location": fee.to_location.name if fee.to_location else None
        }
    
    return {"fee_amount": 0.0, "currency": "EUR", "applies": False}


@router.get("/{fee_id}", response_model=OneWayFeeResponse)
async def get_one_way_fee(
    fee_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get specific one-way fee by ID."""
    fee = db.query(OneWayFee).filter(OneWayFee.id == fee_id).first()
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One-way fee not found"
        )
    return fee_to_response(fee)


@router.post("", response_model=OneWayFeeResponse)
async def create_one_way_fee(
    request: CreateOneWayFeeRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new one-way fee. Only accessible by super admins."""
    
    # Validate locations exist
    from_loc = db.query(Location).filter(Location.id == request.from_location_id).first()
    to_loc = db.query(Location).filter(Location.id == request.to_location_id).first()
    if not from_loc:
        raise HTTPException(status_code=400, detail="From location not found")
    if not to_loc:
        raise HTTPException(status_code=400, detail="To location not found")
    
    if request.from_location_id == request.to_location_id:
        raise HTTPException(status_code=400, detail="From and To locations must be different")
    
    # Check if fee already exists for this route
    existing = db.query(OneWayFee).filter(
        OneWayFee.from_location_id == request.from_location_id,
        OneWayFee.to_location_id == request.to_location_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"One-way fee already exists for {from_loc.name} to {to_loc.name}"
        )
    
    fee = OneWayFee(
        from_location_id=request.from_location_id,
        to_location_id=request.to_location_id,
        fee_amount=Decimal(str(request.fee_amount)),
        currency=request.currency,
        is_active=request.is_active
    )
    
    db.add(fee)
    db.commit()
    db.refresh(fee)
    
    return fee_to_response(fee)


@router.put("/{fee_id}", response_model=OneWayFeeResponse)
async def update_one_way_fee(
    fee_id: int,
    request: UpdateOneWayFeeRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Update a one-way fee. Only accessible by super admins."""
    
    fee = db.query(OneWayFee).filter(OneWayFee.id == fee_id).first()
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One-way fee not found"
        )
    
    if request.from_location_id is not None:
        loc = db.query(Location).filter(Location.id == request.from_location_id).first()
        if not loc:
            raise HTTPException(status_code=400, detail="From location not found")
        fee.from_location_id = request.from_location_id
    if request.to_location_id is not None:
        loc = db.query(Location).filter(Location.id == request.to_location_id).first()
        if not loc:
            raise HTTPException(status_code=400, detail="To location not found")
        fee.to_location_id = request.to_location_id
    if request.fee_amount is not None:
        fee.fee_amount = Decimal(str(request.fee_amount))
    if request.currency is not None:
        fee.currency = request.currency
    if request.is_active is not None:
        fee.is_active = request.is_active
    
    db.commit()
    db.refresh(fee)
    
    return fee_to_response(fee)


@router.delete("/{fee_id}")
async def delete_one_way_fee(
    fee_id: int,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Delete a one-way fee. Only accessible by super admins."""
    
    fee = db.query(OneWayFee).filter(OneWayFee.id == fee_id).first()
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One-way fee not found"
        )
    
    db.delete(fee)
    db.commit()
    
    return {"message": "One-way fee deleted successfully"}
