"""VIPCars email parser"""
from __future__ import annotations

import re
import logging
from datetime import datetime

from .base import BaseEmailParser, ParsedBookingData

logger = logging.getLogger(__name__)


class VIPCarsParser(BaseEmailParser):
    """Parser for VIPCars.com reservation emails"""
    
    def get_broker_name(self) -> str:
        return "VIPCars"
    
    def can_parse(self, email_subject: str, email_body: str, email_from: str) -> bool:
        """Check if this email is from VIPCars"""
        # Check for VIPCars indicators
        if "vipcars.com" in email_from.lower():
            return True
        
        if "vipcars.com" in email_body.lower() and "reservation number" in email_body.lower():
            return True
        
        return False
    
    def parse(self, email_subject: str, email_body: str, email_from: str) -> ParsedBookingData:
        """
        Parse VIPCars email format - gracefully handles missing fields
        """
        warnings = []
        
        # Extract reservation number
        broker_reference = None
        try:
            ref_match = re.search(r'Reservation Number\s*:?\s*([A-Z0-9]+)', email_body)
            broker_reference = ref_match.group(1) if ref_match else None
            if not broker_reference:
                warnings.append("Reservation number not found")
                logger.warning(f"[VIPCars] No reservation number found")
        except Exception as e:
            warnings.append(f"Failed to extract reservation number: {str(e)}")
            logger.error(f"[VIPCars] Error extracting reservation number: {e}")
        
        # Extract first name and surname
        first_name = None
        last_name = None
        try:
            first_name_match = re.search(r'First name\s*:?\s*(.+)', email_body)
            if first_name_match:
                first_name = first_name_match.group(1).strip()
            else:
                warnings.append("First name not found")
                logger.warning(f"[VIPCars] No first name found")
            
            surname_match = re.search(r'Surname\s*:?\s*(.+)', email_body)
            if surname_match:
                last_name = surname_match.group(1).strip()
            else:
                warnings.append("Surname not found")
        except Exception as e:
            warnings.append(f"Failed to extract name: {str(e)}")
            logger.error(f"[VIPCars] Error extracting name: {e}")
        
        # Extract email
        customer_email = None
        try:
            email_match = re.search(r'Email\s*:?\s*([^\s]+@[^\s]+)', email_body)
            if email_match:
                customer_email = email_match.group(1).strip()
            elif first_name and last_name:
                customer_email = f"{first_name.lower()}.{last_name.lower()}@vipcars-booking.com"
                warnings.append("Email not found, generated placeholder")
                logger.info(f"[VIPCars] Generated placeholder email: {customer_email}")
            else:
                warnings.append("Email not found and cannot generate placeholder")
                logger.warning(f"[VIPCars] No email found")
        except Exception as e:
            warnings.append(f"Failed to extract email: {str(e)}")
            logger.error(f"[VIPCars] Error extracting email: {e}")
        
        # Extract phone
        customer_phone = None
        try:
            phone_match = re.search(r'(?:Phone|Mobile)\s*:?\s*([+\d\s\-()]+)', email_body)
            customer_phone = phone_match.group(1).strip() if phone_match else None
            if not customer_phone:
                warnings.append("Phone number not found")
        except Exception as e:
            warnings.append(f"Failed to extract phone: {str(e)}")
            logger.error(f"[VIPCars] Error extracting phone: {e}")
        
        # Extract pickup location and datetime
        pickup_location = None
        pickup_datetime = None
        try:
            pickup_loc_match = re.search(r'Pick up location\s*:?\s*(.+?)(?:\n|$)', email_body)
            if pickup_loc_match:
                pickup_location = pickup_loc_match.group(1).strip()
                pickup_location = re.sub(r'\s*\([^)]+\)', '', pickup_location).strip()
            else:
                warnings.append("Pickup location not found")
                logger.warning(f"[VIPCars] No pickup location found")
            
            pickup_match = re.search(r'Pick up date\s*:?\s*(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})', email_body)
            if pickup_match:
                pickup_date_str = f"{pickup_match.group(1)} {pickup_match.group(2)}"
                pickup_datetime = self._parse_datetime(pickup_date_str, ["%d/%m/%Y %H:%M"])
                logger.info(f"[VIPCars] Parsed pickup: {pickup_location} at {pickup_datetime}")
            else:
                warnings.append("Pickup date not found")
                logger.warning(f"[VIPCars] No pickup date found")
        except Exception as e:
            warnings.append(f"Failed to extract pickup info: {str(e)}")
            logger.error(f"[VIPCars] Error extracting pickup info: {e}")
        
        # Extract dropoff location and datetime
        dropoff_location = None
        dropoff_datetime = None
        try:
            dropoff_loc_match = re.search(r'Drop off location\s*:?\s*(.+?)(?:\n|$)', email_body)
            if dropoff_loc_match:
                dropoff_location = dropoff_loc_match.group(1).strip()
                dropoff_location = re.sub(r'\s*\([^)]+\)', '', dropoff_location).strip()
            else:
                warnings.append("Dropoff location not found")
                logger.warning(f"[VIPCars] No dropoff location found")
            
            dropoff_match = re.search(r'Drop off date\s*:?\s*(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})', email_body)
            if dropoff_match:
                dropoff_date_str = f"{dropoff_match.group(1)} {dropoff_match.group(2)}"
                dropoff_datetime = self._parse_datetime(dropoff_date_str, ["%d/%m/%Y %H:%M"])
                logger.info(f"[VIPCars] Parsed dropoff: {dropoff_location} at {dropoff_datetime}")
            else:
                warnings.append("Dropoff date not found")
                logger.warning(f"[VIPCars] No dropoff date found")
        except Exception as e:
            warnings.append(f"Failed to extract dropoff info: {str(e)}")
            logger.error(f"[VIPCars] Error extracting dropoff info: {e}")
        
        # Extract vehicle info
        vehicle_make = None
        vehicle_model = None
        vehicle_category = None
        try:
            vehicle_match = re.search(r'Selected sample car type\s*:?\s*(.+?)(?:\n|$)', email_body)
            if vehicle_match:
                vehicle_name = vehicle_match.group(1).strip()
                vehicle_name = re.sub(r'\s+or similar.*', '', vehicle_name, flags=re.IGNORECASE).strip()
                parts = vehicle_name.split(' ', 1)
                vehicle_make = parts[0]
                vehicle_model = parts[1] if len(parts) > 1 else None
                logger.info(f"[VIPCars] Parsed vehicle: {vehicle_make} {vehicle_model}")
            else:
                warnings.append("Vehicle info not found")
            
            category_match = re.search(r'Selected car class\s*:?\s*([A-Z0-9]+)', email_body)
            if category_match:
                vehicle_category = category_match.group(1)
        except Exception as e:
            warnings.append(f"Failed to extract vehicle info: {str(e)}")
            logger.error(f"[VIPCars] Error extracting vehicle info: {e}")
        
        # Extract total amount
        total_amount = None
        currency = "EUR"
        try:
            total_match = re.search(r'€\s*([\d,]+\.?\d*)', email_body)
            if total_match:
                total_amount = float(total_match.group(1).replace(',', ''))
                logger.info(f"[VIPCars] Parsed total: {total_amount} {currency}")
            else:
                warnings.append("Total amount not found")
        except Exception as e:
            warnings.append(f"Failed to extract total amount: {str(e)}")
            logger.error(f"[VIPCars] Error extracting total amount: {e}")
        
        # Extract extras
        notes = None
        try:
            extras_match = re.search(r'Requested extras\s*:?\s*(.+?)(?:\n|Any additional)', email_body, re.DOTALL)
            if extras_match and extras_match.group(1).strip():
                notes = f"Extras: {extras_match.group(1).strip()}"
        except Exception as e:
            logger.error(f"[VIPCars] Error extracting extras: {e}")
        
        # Log summary
        logger.info(f"[VIPCars] Parsing complete. Ref: {broker_reference}, Warnings: {len(warnings)}")
        if warnings:
            logger.warning(f"[VIPCars] Parsing warnings: {', '.join(warnings)}")
        
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
            currency=currency,
            broker_reference=broker_reference,
            broker_name=self.broker_name,
            notes=notes,
            parsing_warnings=warnings
        )
