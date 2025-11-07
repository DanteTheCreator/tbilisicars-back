"""Email booking processor - coordinates parsing and booking creation"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .gmail_client import GmailClient
from .registry import registry
from .base import ParsedBookingData

from app.models.booking import Booking
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailBookingProcessor:
    """Process emails and create bookings"""
    
    def __init__(self, db: Session, gmail_client: Optional[GmailClient] = None):
        self.db = db
        self.gmail_client = gmail_client or GmailClient()
    
    def process_unread_emails(self, max_emails: int = 10) -> Dict[str, Any]:
        """
        Fetch and process unread emails
        
        Returns:
            Summary of processing results
        """
        results = {
            'processed': 0,
            'created': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            # Authenticate if needed
            if not self.gmail_client.service:
                self.gmail_client.authenticate()
            
            # Fetch unread emails
            emails = self.gmail_client.fetch_unread_emails(max_results=max_emails)
            
            for email in emails:
                results['processed'] += 1
                
                try:
                    # Try to parse email
                    logger.info(f"Processing email {email['id']}: {email['subject']}")
                    booking_data = registry.parse_email(
                        email['subject'],
                        email['body'],
                        email['from']
                    )
                    
                    if booking_data is None:
                        results['skipped'] += 1
                        logger.info(f"Email {email['id']} skipped - no parser matched")
                        continue
                    
                    # Check if data is valid
                    is_valid, missing_fields = booking_data.is_valid()
                    if not is_valid:
                        logger.error(f"Email {email['id']} - Missing required fields: {', '.join(missing_fields)}")
                        results['failed'] += 1
                        results['errors'].append({
                            'email_id': email['id'],
                            'subject': email['subject'],
                            'error': f"Missing required fields: {', '.join(missing_fields)}",
                            'warnings': booking_data.parsing_warnings
                        })
                        continue
                    
                    # Log parsing warnings
                    if booking_data.parsing_warnings:
                        logger.warning(f"Email {email['id']} - Parsing warnings: {', '.join(booking_data.parsing_warnings)}")
                    
                    # Create booking
                    booking = self._create_booking_from_data(booking_data)
                    
                    if booking:
                        results['created'] += 1
                        logger.info(f"Email {email['id']} - Booking created successfully: {booking.id}")
                        # Mark email as processed
                        self.gmail_client.mark_as_read(email['id'])
                        self.gmail_client.mark_with_label(email['id'], 'Processed')
                    else:
                        results['failed'] += 1
                        logger.error(f"Email {email['id']} - Failed to create booking")
                        
                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    logger.error(f"Email {email['id']} - Error: {error_msg}")
                    results['errors'].append({
                        'email_id': email['id'],
                        'subject': email['subject'],
                        'error': error_msg
                    })
            
        except Exception as e:
            results['errors'].append({'error': f"Failed to fetch emails: {str(e)}"})
        
        return results
    
    def _create_booking_from_data(self, data: ParsedBookingData) -> Optional[Booking]:
        """
        Create a booking from parsed email data - gracefully handles missing data
        
        Args:
            data: ParsedBookingData object
            
        Returns:
            Created Booking object or None if failed
        """
        try:
            logger.info(f"Creating booking for {data.broker_name} ref: {data.broker_reference}")
            
            # Find or create user
            user = self._find_or_create_user(data)
            if not user:
                logger.error("Failed to find or create user")
                raise ValueError("Failed to find or create user")
            
            logger.info(f"User found/created: {user.email}")
            
            # Find locations - try flexible matching
            pickup_location = self._find_location(data.pickup_location_name) if data.pickup_location_name else None
            dropoff_location = self._find_location(data.dropoff_location_name) if data.dropoff_location_name else None
            
            if not pickup_location:
                logger.warning(f"Pickup location not found: {data.pickup_location_name}, using default")
                # Use first available location as fallback
                pickup_location = self.db.query(Location).first()
            
            if not dropoff_location:
                logger.warning(f"Dropoff location not found: {data.dropoff_location_name}, using default")
                dropoff_location = pickup_location  # Same as pickup
            
            if not pickup_location or not dropoff_location:
                logger.error("No locations available in database")
                raise ValueError("Locations not found")
            
            logger.info(f"Locations resolved: pickup={pickup_location.name}, dropoff={dropoff_location.name}")
            
            # Find vehicle - be flexible
            vehicle = self._find_available_vehicle(data)
            if not vehicle:
                logger.warning("No available vehicle found matching criteria, using first available")
                # Fallback to any available vehicle
                vehicle = self.db.query(Vehicle).filter(Vehicle.status == 'AVAILABLE').first()
            
            if not vehicle:
                logger.error("No available vehicles in database")
                raise ValueError("No available vehicle found")
            
            logger.info(f"Vehicle assigned: {vehicle.make} {vehicle.model}")
            
            # Prepare notes with parsing warnings if any
            notes_parts = [f"Broker: {data.broker_name}"]
            if data.broker_reference:
                notes_parts.append(f"Ref: {data.broker_reference}")
            if data.notes:
                notes_parts.append(data.notes)
            if data.parsing_warnings:
                notes_parts.append(f"Parsing warnings: {', '.join(data.parsing_warnings)}")
            
            notes = "\n".join(notes_parts)
            
            # Create booking
            booking = Booking(
                user_id=user.id,
                vehicle_id=vehicle.id,
                pickup_location_id=pickup_location.id,
                dropoff_location_id=dropoff_location.id,
                pickup_datetime=data.pickup_datetime,
                dropoff_datetime=data.dropoff_datetime,
                contact_first_name=data.contact_first_name or "Unknown",
                contact_last_name=data.contact_last_name or "",
                contact_email=data.contact_email or user.email,
                contact_phone=data.contact_phone,
                broker=data.broker_name,  # Set broker field from parsed data
                total_amount=data.total_amount or 0,
                currency=data.currency or "EUR",
                notes=notes
            )
            
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)
            
            logger.info(f"Booking created successfully: ID={booking.id}")
            return booking
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create booking: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to create booking: {str(e)}")
    
    def _find_or_create_user(self, data: ParsedBookingData) -> Optional[User]:
        """Find existing user or create new one"""
        if not data.contact_email:
            logger.error("Cannot find or create user without email")
            return None
        
        user = self.db.query(User).filter(User.email == data.contact_email).first()
        
        if not user:
            logger.info(f"Creating new user: {data.contact_email}")
            user = User(
                email=data.contact_email,
                first_name=data.contact_first_name or "Unknown",
                last_name=data.contact_last_name or "",
                phone=data.contact_phone
            )
            self.db.add(user)
            self.db.flush()
        else:
            logger.info(f"Found existing user: {user.email}")
        
        return user
    
    def _find_location(self, location_name: str) -> Optional[Location]:
        """Find location by name (fuzzy match)"""
        if not location_name:
            return None
        
        logger.debug(f"Looking for location: {location_name}")
        
        # Try exact match first
        location = self.db.query(Location).filter(
            Location.name.ilike(location_name)
        ).first()
        
        if not location:
            # Try partial match
            location = self.db.query(Location).filter(
                Location.name.ilike(f"%{location_name}%")
            ).first()
        
        if not location:
            # Try matching by city
            location = self.db.query(Location).filter(
                Location.city.ilike(f"%{location_name}%")
            ).first()
        
        if location:
            logger.debug(f"Matched location: {location.name}")
        else:
            logger.warning(f"No location found matching: {location_name}")
        
        return location
    
    def _find_available_vehicle(self, data: ParsedBookingData) -> Optional[Vehicle]:
        """Find available vehicle matching criteria"""
        logger.debug(f"Looking for vehicle: category={data.vehicle_category}, make={data.vehicle_make}, model={data.vehicle_model}")
        
        # Simple implementation - find any available vehicle
        query = self.db.query(Vehicle).filter(Vehicle.status == 'AVAILABLE')
        
        # Try to match category/class
        if data.vehicle_category:
            category_vehicle = query.filter(
                Vehicle.vehicle_class.ilike(f"%{data.vehicle_category}%")
            ).first()
            if category_vehicle:
                logger.debug(f"Matched vehicle by category: {category_vehicle.make} {category_vehicle.model}")
                return category_vehicle
        
        # Try to match make
        if data.vehicle_make:
            make_vehicle = query.filter(
                Vehicle.make.ilike(f"%{data.vehicle_make}%")
            ).first()
            if make_vehicle:
                logger.debug(f"Matched vehicle by make: {make_vehicle.make} {make_vehicle.model}")
                return make_vehicle
        
        # Fallback to any available
        any_vehicle = query.first()
        if any_vehicle:
            logger.debug(f"Using fallback vehicle: {any_vehicle.make} {any_vehicle.model}")
        
        return any_vehicle
