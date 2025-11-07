"""API routes for email booking system"""
from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.email_parsers.processor import EmailBookingProcessor
from app.email_parsers.registry import registry
from app.routes.utils import get_db

router = APIRouter(prefix="/email-bookings", tags=["email-bookings"])


@router.post("/process", response_model=Dict[str, Any])
def process_emails(max_emails: int = 10, db: Session = Depends(get_db)):
    """
    Process unread emails and create bookings
    
    Args:
        max_emails: Maximum number of emails to process
    """
    try:
        processor = EmailBookingProcessor(db)
        results = processor.process_unread_emails(max_emails=max_emails)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process emails: {str(e)}"
        )


@router.get("/brokers", response_model=Dict[str, Any])
def list_brokers():
    """List all registered broker parsers"""
    return {
        "brokers": registry.list_brokers(),
        "count": len(registry.list_brokers())
    }
