from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from .utils import get_db, to_dict, apply_updates

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[Dict[str, Any]])
def list_users(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    users = db.query(User).offset(skip).limit(limit).all()
    return [to_dict(u) for u in users]


@router.get("/{user_id}", response_model=Dict[str, Any])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return to_dict(user)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_user(payload: Dict[str, Any], db: Session = Depends(get_db)):
    user = User()
    apply_updates(user, payload)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(user)
    return to_dict(user)


@router.put("/{user_id}", response_model=Dict[str, Any])
def update_user(user_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    apply_updates(user, payload)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig) if getattr(e, "orig", None) else str(e))
    db.refresh(user)
    return to_dict(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return None
