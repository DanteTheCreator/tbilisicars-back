"""Example broker parser - copy this template for new brokers"""
from __future__ import annotations

import re
from datetime import datetime

from .base import BaseEmailParser, ParsedBookingData


class ExampleBrokerParser(BaseEmailParser):
    """Parser for Example Broker reservation emails"""
    
    def get_broker_name(self) -> str:
        return "Example Broker"
    
    def can_parse(self, email_subject: str, email_body: str, email_from: str) -> bool:
        """
        Check if this email is from Example Broker
        """
        # Check sender email domain
        if "example-broker.com" not in email_from.lower():
            return False
        
        # Check for broker-specific keywords in subject
        subject_keywords = ["reservation", "booking confirmed"]
        return any(kw in email_subject.lower() for kw in subject_keywords)
    
    def parse(self, email_subject: str, email_body: str, email_from: str) -> ParsedBookingData:
        """
        Parse Example Broker email format
        
        Example email format:
        ----------------------
        Booking Reference: EB123456
        
        Customer Details:
        Name: John Doe
        Email: john@example.com
        Phone: +1234567890
        
        Pickup: 2025-11-01 10:00 at Airport Location
        Dropoff: 2025-11-05 10:00 at Airport Location
        
        Vehicle: Toyota Camry (Midsize)
        Total: $250.00
        """
        try:
            # Extract booking reference
            ref_match = re.search(r'Booking Reference:\s*(\w+)', email_body)
            broker_reference = ref_match.group(1) if ref_match else None
            
            # Extract customer name
            name_match = re.search(r'Name:\s*(.+)', email_body)
            if not name_match:
                raise ValueError("Customer name not found")
            full_name = name_match.group(1).strip()
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Extract email
            email_match = re.search(r'Email:\s*([^\s]+@[^\s]+)', email_body)
            if not email_match:
                raise ValueError("Customer email not found")
            customer_email = email_match.group(1)
            
            # Extract phone
            phone_match = re.search(r'Phone:\s*([+\d\s\-()]+)', email_body)
            customer_phone = phone_match.group(1).strip() if phone_match else None
            
            # Extract pickup datetime and location
            pickup_match = re.search(r'Pickup:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+at\s+(.+)', email_body)
            if not pickup_match:
                raise ValueError("Pickup information not found")
            pickup_datetime = self._parse_datetime(pickup_match.group(1), ["%Y-%m-%d %H:%M"])
            pickup_location = pickup_match.group(2).strip()
            
            # Extract dropoff datetime and location
            dropoff_match = re.search(r'Dropoff:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+at\s+(.+)', email_body)
            if not dropoff_match:
                raise ValueError("Dropoff information not found")
            dropoff_datetime = self._parse_datetime(dropoff_match.group(1), ["%Y-%m-%d %H:%M"])
            dropoff_location = dropoff_match.group(2).strip()
            
            # Extract vehicle info
            vehicle_match = re.search(r'Vehicle:\s*([^\(]+)\s*\(([^\)]+)\)', email_body)
            vehicle_name = vehicle_match.group(1).strip() if vehicle_match else None
            vehicle_category = vehicle_match.group(2).strip() if vehicle_match else None
            
            # Parse vehicle name into make/model
            vehicle_make = None
            vehicle_model = None
            if vehicle_name:
                parts = vehicle_name.split(' ', 1)
                vehicle_make = parts[0]
                vehicle_model = parts[1] if len(parts) > 1 else None
            
            # Extract total amount
            total_match = re.search(r'Total:\s*\$?([\d,]+\.?\d*)', email_body)
            total_amount = float(total_match.group(1).replace(',', '')) if total_match else None
            
            return ParsedBookingData(
                pickup_datetime=pickup_datetime,
                dropoff_datetime=dropoff_datetime,
                pickup_location_name=pickup_location,
                dropoff_location_name=dropoff_location,
                contact_first_name=first_name,
                contact_last_name=last_name,
                contact_email=customer_email,
                contact_phone=customer_phone,
                vehicle_make=vehicle_make,
                vehicle_model=vehicle_model,
                vehicle_category=vehicle_category,
                total_amount=total_amount,
                currency="USD",
                broker_reference=broker_reference,
                broker_name=self.broker_name
            )
            
        except Exception as e:
            raise ValueError(f"Failed to parse {self.broker_name} email: {str(e)}")
