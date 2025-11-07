from __future__ import annotations

from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_super_admin
from app.core.db import get_db
from app.models.one_way_fee import OneWayFee
from app.models.admin import Admin

router = APIRouter(prefix="/admin/one-way-fees", tags=["One-Way Fees"])


class OneWayFeeResponse(BaseModel):
    id: int
    from_city: str
    to_city: str
    fee_amount: float
    currency: str
    is_active: bool
    created_at: str


class CreateOneWayFeeRequest(BaseModel):
    from_city: str
    to_city: str
    fee_amount: float
    currency: str = "EUR"
    is_active: bool = True


class UpdateOneWayFeeRequest(BaseModel):
    from_city: Optional[str] = None
    to_city: Optional[str] = None
    fee_amount: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


def fee_to_response(fee: OneWayFee) -> OneWayFeeResponse:
    """Convert OneWayFee model to response."""
    return OneWayFeeResponse(
        id=fee.id,
        from_city=fee.from_city,
        to_city=fee.to_city,
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
    fees = db.query(OneWayFee).order_by(OneWayFee.from_city, OneWayFee.to_city).all()
    return [fee_to_response(fee) for fee in fees]


@router.get("/active", response_model=List[OneWayFeeResponse])
async def list_active_one_way_fees(
    db: Session = Depends(get_db)
):
    """Get list of active one-way fees (public endpoint)."""
    fees = db.query(OneWayFee).filter(OneWayFee.is_active == True).order_by(OneWayFee.from_city, OneWayFee.to_city).all()
    return [fee_to_response(fee) for fee in fees]


@router.get("/calculate")
async def calculate_one_way_fee(
    from_city: str,
    to_city: str,
    db: Session = Depends(get_db)
):
    """Calculate one-way fee for given cities."""
    if from_city.lower() == to_city.lower():
        return {"fee_amount": 0.0, "currency": "EUR", "applies": False}
    
    # Try to find exact match
    fee = db.query(OneWayFee).filter(
        OneWayFee.from_city.ilike(from_city),
        OneWayFee.to_city.ilike(to_city),
        OneWayFee.is_active == True
    ).first()
    
    if fee:
        return {
            "fee_amount": float(fee.fee_amount),
            "currency": fee.currency,
            "applies": True,
            "from_city": fee.from_city,
            "to_city": fee.to_city
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
    
    # Check if fee already exists
    existing = db.query(OneWayFee).filter(
        OneWayFee.from_city.ilike(request.from_city),
        OneWayFee.to_city.ilike(request.to_city)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"One-way fee already exists for {request.from_city} to {request.to_city}"
        )
    
    fee = OneWayFee(
        from_city=request.from_city,
        to_city=request.to_city,
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
    
    if request.from_city is not None:
        fee.from_city = request.from_city
    if request.to_city is not None:
        fee.to_city = request.to_city
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
