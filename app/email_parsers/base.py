"""Base email parser for broker reservation emails"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ParsedBookingData:
    """Structured booking data extracted from email"""
    
    # Required: Booking details (dates and times)
    pickup_datetime: Optional[datetime] = None
    dropoff_datetime: Optional[datetime] = None
    
    # Required: Locations
    pickup_location_name: Optional[str] = None
    dropoff_location_name: Optional[str] = None
    
    # Required: Customer info (at least one identifier)
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # Optional: Vehicle info
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_category: Optional[str] = None
    
    # Optional: Pricing
    total_amount: Optional[float] = None
    currency: str = "EUR"
    
    # Optional: Broker info
    broker_reference: Optional[str] = None
    broker_name: str = ""
    
    # Additional data
    extras: Dict[str, Any] = None
    notes: Optional[str] = None
    
    # Parsing warnings/errors
    parsing_warnings: list[str] = None
    
    def __post_init__(self):
        if self.extras is None:
            self.extras = {}
        if self.parsing_warnings is None:
            self.parsing_warnings = []
    
    def is_valid(self) -> tuple[bool, list[str]]:
        """
        Check if the parsed data has minimum required fields
        
        Returns:
            (is_valid, list_of_missing_fields)
        """
        missing = []
        
        if not self.pickup_datetime:
            missing.append("pickup_datetime")
        if not self.dropoff_datetime:
            missing.append("dropoff_datetime")
        if not self.pickup_location_name:
            missing.append("pickup_location_name")
        if not self.dropoff_location_name:
            missing.append("dropoff_location_name")
        
        # Need at least one customer identifier
        if not self.contact_first_name and not self.contact_email:
            missing.append("contact_first_name or contact_email")
        
        return (len(missing) == 0, missing)


class BaseEmailParser(ABC):
    """Base class for all broker email parsers"""
    
    def __init__(self):
        self.broker_name = self.get_broker_name()
    
    @abstractmethod
    def get_broker_name(self) -> str:
        """Return the broker name this parser handles"""
        pass
    
    @abstractmethod
    def can_parse(self, email_subject: str, email_body: str, email_from: str) -> bool:
        """
        Determine if this parser can handle the given email
        
        Args:
            email_subject: Email subject line
            email_body: Email body (plain text or HTML)
            email_from: Sender email address
            
        Returns:
            True if this parser can handle the email
        """
        pass
    
    @abstractmethod
    def parse(self, email_subject: str, email_body: str, email_from: str) -> ParsedBookingData:
        """
        Parse the email and extract booking data
        
        Args:
            email_subject: Email subject line
            email_body: Email body (plain text or HTML)
            email_from: Sender email address
            
        Returns:
            ParsedBookingData object with extracted information
            
        Raises:
            ValueError: If required data cannot be extracted
        """
        pass
    
    def _parse_datetime(self, date_str: str, formats: list[str]) -> datetime:
        """
        Helper to parse datetime from various formats
        
        Args:
            date_str: Date string to parse
            formats: List of datetime format strings to try
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If date cannot be parsed
        """
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        raise ValueError(f"Could not parse date: {date_str}")
