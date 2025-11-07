"""
Example broker email parser - use as template for creating new parsers.
Copy this file and modify for each broker.
"""
from email.message import EmailMessage
from datetime import datetime
import re

from app.core.email_parser import EmailParser, ParsedBooking


class ExampleBrokerParser(EmailParser):
    """
    Parser for Example Broker emails.
    
    Email characteristics:
    - Sender: reservations@examplebroker.com
    - Subject: Contains "New Reservation" or "Booking Confirmation"
    """
    
    def can_parse(self, email: EmailMessage) -> bool:
        """Check if email is from Example Broker"""
        sender = email.get("From", "").lower()
        subject = email.get("Subject", "").lower()
        
        # Check sender domain
        if "examplebroker.com" in sender:
            return True
        
        # Alternative: check subject pattern
        if "example broker" in subject and "reservation" in subject:
            return True
        
        return False
    
    def parse(self, email: EmailMessage) -> ParsedBooking:
        """
        Parse booking information from Example Broker email.
        
        Expected email format:
        - Plain text with key-value pairs
        - Dates in format: "MM/DD/YYYY HH:MM"
        - Price with currency symbol
        """
        body = self.get_email_body(email)
        subject = email.get("Subject", "")
        
        try:
            # Extract customer information
            first_name = self._extract_field(body, r"First Name:\s*(.+)")
            last_name = self._extract_field(body, r"Last Name:\s*(.+)")
            email_addr = self._extract_field(body, r"Email:\s*(.+)")
            phone = self._extract_field(body, r"Phone:\s*(.+)", required=False)
            
            # Extract dates and locations
            pickup_date_str = self._extract_field(body, r"Pick-up Date:\s*(.+)")
            dropoff_date_str = self._extract_field(body, r"Drop-off Date:\s*(.+)")
            pickup_location = self._extract_field(body, r"Pick-up Location:\s*(.+)")
            dropoff_location = self._extract_field(body, r"Drop-off Location:\s*(.+)")
            
            # Parse dates
            pickup_datetime = datetime.strptime(pickup_date_str.strip(), "%m/%d/%Y %H:%M")
            dropoff_datetime = datetime.strptime(dropoff_date_str.strip(), "%m/%d/%Y %H:%M")
            
            # Extract vehicle information
            vehicle_class = self._extract_field(body, r"Vehicle Class:\s*(.+)", required=False)
            vehicle_make = self._extract_field(body, r"Make:\s*(.+)", required=False)
            vehicle_model = self._extract_field(body, r"Model:\s*(.+)", required=False)
            
            # Extract pricing
            total_str = self._extract_field(body, r"Total Amount:\s*\$?([\d,]+\.?\d*)")
            total_amount = float(total_str.replace(",", ""))
            
            # Extract reference number
            reference = self._extract_field(body, r"Confirmation #:\s*(.+)", required=False)
            
            # Extract extras if present
            extras = self._extract_extras(body)
            
            # Extract notes
            notes = self._extract_field(body, r"Special Instructions:\s*(.+)", required=False)
            
            return ParsedBooking(
                customer_first_name=first_name,
                customer_last_name=last_name,
                customer_email=email_addr,
                customer_phone=phone,
                pickup_datetime=pickup_datetime,
                dropoff_datetime=dropoff_datetime,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                vehicle_class=vehicle_class,
                vehicle_make=vehicle_make,
                vehicle_model=vehicle_model,
                total_amount=total_amount,
                currency="USD",
                broker_name=self.broker_name,
                broker_reference=reference,
                notes=notes,
                extras=extras,
                raw_email_subject=subject,
                raw_email_body=body
            )
            
        except Exception as e:
            raise ValueError(f"Failed to parse Example Broker email: {str(e)}")
    
    def _extract_field(self, text: str, pattern: str, required: bool = True) -> str:
        """Extract a field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        elif required:
            raise ValueError(f"Required field not found: {pattern}")
        return None
    
    def _extract_extras(self, text: str) -> list[str]:
        """Extract list of extras/add-ons"""
        extras = []
        
        # Look for extras section
        extras_match = re.search(r"Extras?:(.*?)(?=\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
        if extras_match:
            extras_text = extras_match.group(1)
            # Split by newlines and clean up
            for line in extras_text.split("\n"):
                line = line.strip()
                if line and not line.startswith("-"):
                    extras.append(line)
        
        return extras if extras else None
