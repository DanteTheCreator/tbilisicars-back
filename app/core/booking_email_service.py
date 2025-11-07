"""
Service for processing booking emails and creating reservations in the database.
"""
from __future__ import annotations

from email.message import EmailMessage
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.email_parser import EmailParserRegistry, ParsedBooking
from app.models.booking import Booking, BookingStatusEnum, PaymentStatusEnum
from app.models.location import Location
from app.models.vehicle_group import VehicleGroup
from app.models.vehicle import Vehicle
from app.models.user import User


class BookingEmailProcessor:
    """Process booking emails and create database records"""
    
    def __init__(self, parser_registry: EmailParserRegistry):
        self.parser_registry = parser_registry
    
    def process_email(self, email: EmailMessage, db: Session) -> Optional[int]:
        """
        Process an email and create a booking if valid.
        
        Args:
            email: Email message object
            db: Database session
            
        Returns:
            booking_id if successful, None if email couldn't be parsed
            
        Raises:
            ValueError: If parsing fails or required data is invalid
            IntegrityError: If database constraints are violated
        """
        # Parse email
        parsed = self.parser_registry.parse_email(email)
        if not parsed:
            return None
        
        # Create booking from parsed data
        booking_id = self._create_booking_from_parsed(parsed, db)
        return booking_id
    
    def _create_booking_from_parsed(self, parsed: ParsedBooking, db: Session) -> int:
        """Create a booking record from parsed data"""
        
        # Find or create user
        user = self._find_or_create_user(parsed, db)
        
        # Map locations
        pickup_location_id = self._map_location(parsed.pickup_location, db)
        dropoff_location_id = self._map_location(parsed.dropoff_location, db)
        
        # Find available vehicle
        vehicle_id = self._find_available_vehicle(
            parsed.vehicle_class, 
            parsed.pickup_datetime, 
            parsed.dropoff_datetime,
            db
        )
        
        if not vehicle_id:
            raise ValueError(f"No available vehicle found for class: {parsed.vehicle_class}")
        
        # Create booking
        booking = Booking(
            user_id=user.id,
            vehicle_id=vehicle_id,
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            pickup_datetime=parsed.pickup_datetime,
            dropoff_datetime=parsed.dropoff_datetime,
            status=BookingStatusEnum.PENDING,
            payment_status=PaymentStatusEnum.UNPAID,
            total_amount=parsed.total_amount,
            currency=parsed.currency,
            contact_first_name=parsed.customer_first_name,
            contact_last_name=parsed.customer_last_name,
            contact_email=parsed.customer_email,
            contact_phone=parsed.customer_phone,
            notes=self._build_notes(parsed)
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return booking.id
    
    def _find_or_create_user(self, parsed: ParsedBooking, db: Session) -> User:
        """Find existing user or create new one"""
        user = db.query(User).filter(User.email == parsed.customer_email).first()
        
        if not user:
            user = User(
                email=parsed.customer_email,
                first_name=parsed.customer_first_name,
                last_name=parsed.customer_last_name,
                phone=parsed.customer_phone,
                is_active=True
            )
            db.add(user)
            db.flush()  # Get user.id without committing
        
        return user
    
    def _map_location(self, location_name: str, db: Session) -> int:
        """Map location name to location_id"""
        # Try exact match first
        location = db.query(Location).filter(
            Location.name.ilike(location_name)
        ).first()
        
        if location:
            return location.id
        
        # Try partial match
        location = db.query(Location).filter(
            Location.name.ilike(f"%{location_name}%")
        ).first()
        
        if location:
            return location.id
        
        raise ValueError(f"Location not found: {location_name}")
    
    def _find_available_vehicle(
        self, 
        vehicle_class: Optional[str], 
        pickup: datetime, 
        dropoff: datetime,
        db: Session
    ) -> Optional[int]:
        """Find an available vehicle for the booking period"""
        
        # Build query
        query = db.query(Vehicle).filter(
            Vehicle.active == True,
            Vehicle.status == "AVAILABLE"
        )
        
        # Filter by vehicle group if class specified
        if vehicle_class:
            group = db.query(VehicleGroup).filter(
                VehicleGroup.name.ilike(f"%{vehicle_class}%")
            ).first()
            
            if group:
                query = query.filter(Vehicle.vehicle_group_id == group.id)
        
        # Check availability (no overlapping bookings)
        available_vehicles = []
        for vehicle in query.all():
            has_conflict = db.query(Booking).filter(
                Booking.vehicle_id == vehicle.id,
                Booking.status.in_([BookingStatusEnum.CONFIRMED, BookingStatusEnum.PENDING]),
                Booking.pickup_datetime < dropoff,
                Booking.dropoff_datetime > pickup
            ).first()
            
            if not has_conflict:
                available_vehicles.append(vehicle.id)
        
        return available_vehicles[0] if available_vehicles else None
    
    def _build_notes(self, parsed: ParsedBooking) -> str:
        """Build notes field from parsed data"""
        notes_parts = []
        
        notes_parts.append(f"Source: {parsed.broker_name}")
        
        if parsed.broker_reference:
            notes_parts.append(f"Reference: {parsed.broker_reference}")
        
        if parsed.extras:
            notes_parts.append(f"Extras: {', '.join(parsed.extras)}")
        
        if parsed.notes:
            notes_parts.append(f"Special Instructions: {parsed.notes}")
        
        return "\n".join(notes_parts)
