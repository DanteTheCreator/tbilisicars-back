"""DiscoverCars email parser"""
from __future__ import annotations

import re
import logging
from datetime import datetime

from .base import BaseEmailParser, ParsedBookingData

logger = logging.getLogger(__name__)


class DiscoverCarsParser(BaseEmailParser):
    """Parser for Discover Cars reservation emails"""
    
    def get_broker_name(self) -> str:
        return "Discover Cars"
    
    def can_parse(self, email_subject: str, email_body: str, email_from: str) -> bool:
        """Check if this email is from Discover Cars"""
        # Check for Discover Cars indicators
        if "discovercars" in email_from.lower() or "discover cars" in email_from.lower():
            return True
        
        if "discover cars" in email_body.lower() and "booking number" in email_body.lower():
            return True
        
        return False
    
    def parse(self, email_subject: str, email_body: str, email_from: str) -> ParsedBookingData:
        """
        Parse Discover Cars email format
        
        Format:
        - Discover Cars booking number: D012182965-42RR
        - Pick-up: Georgia, Batumi, Downtown, 28 Oct 2025, 18:00
        - Drop-off: Georgia, Batumi, Downtown, 31 Oct 2025, 18:00
        - Driver name: Ido Ofir
        - Date of birth: 6 Mar 1981
        - Vehicle class sample: Toyota Prius or similar
        - Voucher value: 82.24 EUR
        """
        warnings = []
        
        # Extract booking reference
        broker_reference = None
        try:
            ref_match = re.search(r'Discover Cars booking number\s*:?\s*([A-Z0-9\-]+)', email_body)
            broker_reference = ref_match.group(1) if ref_match else None
            if not broker_reference:
                warnings.append("Booking reference not found")
                logger.warning(f"[DiscoverCars] No booking reference found in email")
        except Exception as e:
            warnings.append(f"Failed to extract booking reference: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting booking reference: {e}")
        
        # Extract driver name
        first_name = None
        last_name = None
        try:
            name_match = re.search(r'Driver name\s*:?\s*(.+)', email_body)
            if name_match:
                full_name = name_match.group(1).strip()
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
            else:
                warnings.append("Driver name not found")
                logger.warning(f"[DiscoverCars] No driver name found")
        except Exception as e:
            warnings.append(f"Failed to extract driver name: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting driver name: {e}")
        
        # Extract email if available
        customer_email = None
        try:
            email_match = re.search(r'Email\s*:?\s*([^\s]+@[^\s]+)', email_body)
            if email_match:
                customer_email = email_match.group(1).strip()
            elif first_name and last_name:
                # Generate placeholder email
                customer_email = f"{first_name.lower()}.{last_name.lower()}@discover-booking.com"
                warnings.append("Email not found, generated placeholder")
                logger.info(f"[DiscoverCars] Generated placeholder email: {customer_email}")
            else:
                warnings.append("Email not found and cannot generate placeholder")
                logger.warning(f"[DiscoverCars] No email found")
        except Exception as e:
            warnings.append(f"Failed to extract email: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting email: {e}")
        
        # Extract phone if available
        customer_phone = None
        try:
            phone_match = re.search(r'(?:Phone|Mobile)\s*:?\s*([+\d\s\-()]+)', email_body)
            customer_phone = phone_match.group(1).strip() if phone_match else None
            if not customer_phone:
                warnings.append("Phone number not found")
        except Exception as e:
            warnings.append(f"Failed to extract phone: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting phone: {e}")
        
        # Extract pickup info
        pickup_location = None
        pickup_datetime = None
        try:
            pickup_match = re.search(r'Pick-up\s*:?\s*(?:[^,]+,\s*)?([^,]+),\s*([^,]+),\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*(\d{2}:\d{2})', email_body)
            if pickup_match:
                pickup_city = pickup_match.group(1).strip()
                pickup_area = pickup_match.group(2).strip()
                pickup_date_str = f"{pickup_match.group(3)} {pickup_match.group(4)}"
                
                pickup_location = f"{pickup_city}, {pickup_area}"
                pickup_datetime = self._parse_datetime(pickup_date_str, ["%d %b %Y %H:%M"])
                logger.info(f"[DiscoverCars] Parsed pickup: {pickup_location} at {pickup_datetime}")
            else:
                warnings.append("Pickup information not found")
                logger.warning(f"[DiscoverCars] No pickup info found")
        except Exception as e:
            warnings.append(f"Failed to extract pickup info: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting pickup info: {e}")
        
        # Extract dropoff info
        dropoff_location = None
        dropoff_datetime = None
        try:
            dropoff_match = re.search(r'Drop-off\s*:?\s*(?:[^,]+,\s*)?([^,]+),\s*([^,]+),\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*(\d{2}:\d{2})', email_body)
            if dropoff_match:
                dropoff_city = dropoff_match.group(1).strip()
                dropoff_area = dropoff_match.group(2).strip()
                dropoff_date_str = f"{dropoff_match.group(3)} {dropoff_match.group(4)}"
                
                dropoff_location = f"{dropoff_city}, {dropoff_area}"
                dropoff_datetime = self._parse_datetime(dropoff_date_str, ["%d %b %Y %H:%M"])
                logger.info(f"[DiscoverCars] Parsed dropoff: {dropoff_location} at {dropoff_datetime}")
            else:
                warnings.append("Dropoff information not found")
                logger.warning(f"[DiscoverCars] No dropoff info found")
        except Exception as e:
            warnings.append(f"Failed to extract dropoff info: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting dropoff info: {e}")
        
        # Extract vehicle info
        vehicle_make = None
        vehicle_model = None
        vehicle_category = None
        try:
            vehicle_match = re.search(r'Vehicle class sample\s*:?\s*(.+?)(?:\n|$)', email_body)
            if vehicle_match:
                vehicle_name = vehicle_match.group(1).strip()
                vehicle_name = re.sub(r'\s+or similar.*', '', vehicle_name, flags=re.IGNORECASE).strip()
                parts = vehicle_name.split(' ', 1)
                vehicle_make = parts[0]
                vehicle_model = parts[1] if len(parts) > 1 else None
                logger.info(f"[DiscoverCars] Parsed vehicle: {vehicle_make} {vehicle_model}")
            else:
                warnings.append("Vehicle info not found")
            
            # Extract vehicle category
            category_match = re.search(r'Vehicle class\s*:?\s*([A-Za-z]+)', email_body)
            if category_match:
                vehicle_category = category_match.group(1)
            else:
                # Try SIPP code
                sipp_match = re.search(r'Vehicle SIPP code\s*:?\s*([A-Z0-9]+)', email_body)
                if sipp_match:
                    vehicle_category = sipp_match.group(1)
        except Exception as e:
            warnings.append(f"Failed to extract vehicle info: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting vehicle info: {e}")
        
        # Extract voucher value
        total_amount = None
        currency = "EUR"
        try:
            total_match = re.search(r'Voucher value\s*:?\s*([\d,]+\.?\d*)\s*(EUR|USD|GEL)', email_body)
            if total_match:
                total_amount = float(total_match.group(1).replace(',', ''))
                currency = total_match.group(2)
                logger.info(f"[DiscoverCars] Parsed total: {total_amount} {currency}")
            else:
                warnings.append("Total amount not found")
        except Exception as e:
            warnings.append(f"Failed to extract total amount: {str(e)}")
            logger.error(f"[DiscoverCars] Error extracting total amount: {e}")
        
        # Extract pickup/dropoff instructions as notes
        notes_parts = []
        try:
            pickup_inst = re.search(r'Pick-up Instructions\s*:?\s*(.+?)(?:\n(?:Drop-off|Supplier|Driver)|$)', email_body, re.DOTALL)
            if pickup_inst and pickup_inst.group(1).strip():
                notes_parts.append(f"Pickup: {pickup_inst.group(1).strip()}")
            
            dropoff_inst = re.search(r'Drop-off Instructions\s*:?\s*(.+?)(?:\n(?:Supplier|Driver|Vehicle)|$)', email_body, re.DOTALL)
            if dropoff_inst and dropoff_inst.group(1).strip():
                notes_parts.append(f"Dropoff: {dropoff_inst.group(1).strip()}")
        except Exception as e:
            logger.error(f"[DiscoverCars] Error extracting instructions: {e}")
        
        notes = " | ".join(notes_parts) if notes_parts else None
        
        # Log summary
        logger.info(f"[DiscoverCars] Parsing complete. Ref: {broker_reference}, Warnings: {len(warnings)}")
        if warnings:
            logger.warning(f"[DiscoverCars] Parsing warnings: {', '.join(warnings)}")
        
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
