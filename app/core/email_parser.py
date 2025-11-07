"""
Email parser base classes for extracting booking information from broker emails.
Each broker has its own parser implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass
class ParsedBooking:
    """Standardized booking data extracted from email"""
    # Customer info (required)
    customer_first_name: str
    customer_last_name: str
    customer_email: str

    # Booking details (required)
    pickup_datetime: datetime
    dropoff_datetime: datetime
    pickup_location: str  # Will need to map to location_id
    dropoff_location: str  # Will need to map to location_id

    # Pricing and broker (required)
    total_amount: float
    broker_name: str

    # Optional / defaulted fields
    currency: str = "USD"
    customer_phone: Optional[str] = None

    # Vehicle info
    vehicle_class: Optional[str] = None  # Will need to map to vehicle_group_id
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None

    # Broker reference
    broker_reference: Optional[str] = None  # Confirmation/reference number

    # Additional info
    notes: Optional[str] = None
    extras: Optional[list[str]] = None  # List of extra items requested

    # Raw email for reference
    raw_email_subject: Optional[str] = None
    raw_email_body: Optional[str] = None


class EmailParser(ABC):
    """Base class for email parsers"""
    
    def __init__(self):
        self.broker_name = self.__class__.__name__.replace("Parser", "")
    
    @abstractmethod
    def can_parse(self, email: EmailMessage) -> bool:
        """
        Check if this parser can handle the given email.
        Usually checks sender address or subject line patterns.
        
        Args:
            email: Email message object
            
        Returns:
            True if this parser can handle the email
        """
        pass
    
    @abstractmethod
    def parse(self, email: EmailMessage) -> ParsedBooking:
        """
        Extract booking information from email.
        
        Args:
            email: Email message object
            
        Returns:
            ParsedBooking object with extracted data
            
        Raises:
            ValueError: If email cannot be parsed or required data is missing
        """
        pass
    
    def get_email_body(self, email: EmailMessage) -> str:
        """Extract plain text body from email"""
        body = ""
        if email.is_multipart():
            for part in email.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email.get_payload(decode=True).decode('utf-8', errors='ignore')
        return body
    
    def get_email_html(self, email: EmailMessage) -> Optional[str]:
        """Extract HTML body from email"""
        if email.is_multipart():
            for part in email.walk():
                if part.get_content_type() == "text/html":
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        return None


class EmailParserRegistry:
    """Registry for managing multiple email parsers"""
    
    def __init__(self):
        self.parsers: list[EmailParser] = []
    
    def register(self, parser: EmailParser):
        """Register a new parser"""
        self.parsers.append(parser)
    
    def parse_email(self, email: EmailMessage) -> Optional[ParsedBooking]:
        """
        Try to parse email with registered parsers.
        
        Args:
            email: Email message object
            
        Returns:
            ParsedBooking if successful, None if no parser can handle the email
            
        Raises:
            ValueError: If parser fails during parsing
        """
        for parser in self.parsers:
            if parser.can_parse(email):
                return parser.parse(email)
        return None
    
    def get_parser_for_email(self, email: EmailMessage) -> Optional[EmailParser]:
        """Get the parser that can handle this email"""
        for parser in self.parsers:
            if parser.can_parse(email):
                return parser
        return None
