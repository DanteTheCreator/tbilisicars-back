from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.damage import DamageReport
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/damages", tags=["damages"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_damages(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    items = db.query(DamageReport).offset(skip).limit(limit).all()
    return [to_dict(i) for i in items]


@router.get("/{item_id}", response_model=Dict[str, Any])
def get_damage(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(DamageReport, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DamageReport not found")
    return to_dict(obj)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_damage(payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = DamageReport()
    apply_updates(obj, payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.put("/{item_id}", response_model=Dict[str, Any])
def update_damage(item_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    obj = db.get(DamageReport, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DamageReport not found")
    apply_updates(obj, payload)
    db.commit()
    db.refresh(obj)
    return to_dict(obj)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_damage(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(DamageReport, item_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DamageReport not found")
    db.delete(obj)
    db.commit()
    return None
