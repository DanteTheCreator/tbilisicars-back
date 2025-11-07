"""
API endpoint for processing booking emails.
"""
from __future__ import annotations

from typing import Dict, Any
from email.message import EmailMessage
from email import message_from_string

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.core.email_parser import EmailParserRegistry
from app.core.booking_email_service import BookingEmailProcessor
from app.parsers import ExampleBrokerParser
# Import other parsers as needed
# from app.parsers.broker_a import BrokerAParser

from app.routes.utils import get_db

router = APIRouter(prefix="/booking-emails", tags=["booking-emails"])

# Initialize parser registry
parser_registry = EmailParserRegistry()
parser_registry.register(ExampleBrokerParser())
# Register other parsers
# parser_registry.register(BrokerAParser())

# Initialize email processor
email_processor = BookingEmailProcessor(parser_registry)


@router.post("/process", response_model=Dict[str, Any])
def process_booking_email(
    email_content: str = Body(..., description="Raw email content (RFC 822 format)"),
    db: Session = Depends(get_db)
):
    """
    Process a booking email and create a reservation.
    
    Send the raw email content (including headers) as text.
    The system will identify the broker and extract booking information.
    """
    try:
        # Parse email
        email = message_from_string(email_content)
        
        # Process email
        booking_id = email_processor.process_email(email, db)
        
        if booking_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not identify broker or parse email"
            )
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": "Booking created successfully from email"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process email: {str(e)}"
        )


@router.get("/parsers", response_model=Dict[str, Any])
def list_parsers():
    """List all registered email parsers"""
    return {
        "parsers": [
            {
                "name": parser.broker_name,
                "class": parser.__class__.__name__
            }
            for parser in parser_registry.parsers
        ]
    }
