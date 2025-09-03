from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.vehicle import Vehicle
from app.models.booking import Booking
from app.models.user import User
from app.models.payment import Payment, PaymentStatusEnum

router = APIRouter()

@router.get("/admin/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get dashboard statistics for admin panel
    """
    try:
        # Total vehicles
        total_vehicles = db.query(Vehicle).count()
        
        # Available vehicles
        available_vehicles = db.query(Vehicle).filter(
            Vehicle.status == 'available'
        ).count()
        
                # Active bookings (current)
        now = datetime.now()
        active_bookings = db.query(Booking).filter(
            and_(
                Booking.pickup_datetime <= now,
                Booking.dropoff_datetime >= now,
                Booking.status.in_(['confirmed', 'checked_out'])
            )
        ).count()
        
        # Total users
        total_users = db.query(User).count()
        
        # Monthly revenue (current month) - simplified query for now
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.created_at >= start_of_month
        ).scalar() or 0
        
        # Previous month revenue for growth calculation
        start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)
        end_of_last_month = start_of_month - timedelta(seconds=1)
        last_month_revenue = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.created_at >= start_of_last_month,
                Payment.created_at <= end_of_last_month
            )
        ).scalar() or 0
        
        # Revenue growth percentage
        revenue_growth = 0
        if last_month_revenue > 0:
            revenue_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
        
        # Bookings this week vs last week
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        bookings_this_week = db.query(Booking).filter(
            Booking.created_at >= start_of_week
        ).count()
        
        start_of_last_week = start_of_week - timedelta(days=7)
        end_of_last_week = start_of_week - timedelta(seconds=1)
        
        bookings_last_week = db.query(Booking).filter(
            and_(
                Booking.created_at >= start_of_last_week,
                Booking.created_at <= end_of_last_week
            )
        ).count()
        
        # Booking growth percentage
        booking_growth = 0
        if bookings_last_week > 0:
            booking_growth = ((bookings_this_week - bookings_last_week) / bookings_last_week) * 100
        
        # Vehicle utilization rate
        utilization_rate = 0
        if total_vehicles > 0:
            utilization_rate = (active_bookings / total_vehicles) * 100
        
        # Recent activity (last 10 bookings)
        recent_bookings = db.query(Booking).order_by(Booking.created_at.desc()).limit(10).all()
        recent_activity = []
        for booking in recent_bookings:
            recent_activity.append({
                "id": booking.id,
                "type": "booking",
                "description": f"New booking for {booking.vehicle.make} {booking.vehicle.model}",
                "timestamp": booking.created_at.isoformat(),
                "status": booking.status
            })
        
        # Sort recent activity by timestamp
        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_activity = recent_activity[:15]  # Keep only top 15
        
        return {
            "total_vehicles": total_vehicles,
            "available_vehicles": available_vehicles,
            "active_bookings": active_bookings,
            "total_users": total_users,
            "monthly_revenue": float(monthly_revenue),
            "revenue_growth": round(revenue_growth, 2),
            "booking_growth": round(booking_growth, 2),
            "utilization_rate": round(utilization_rate, 2),
            "bookings_this_week": bookings_this_week,
            "bookings_last_week": bookings_last_week,
            "recent_activity": recent_activity
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "total_vehicles": 0,
            "available_vehicles": 0,
            "active_bookings": 0,
            "total_users": 0,
            "monthly_revenue": 0,
            "revenue_growth": 0,
            "booking_growth": 0,
            "utilization_rate": 0,
            "bookings_this_week": 0,
            "bookings_last_week": 0
        }

@router.get("/admin/recent-activity")
async def get_recent_activity(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    limit: int = 20
):
    """
    Get recent activity for admin dashboard
    """
    try:
        activities = []
        
        # Recent bookings
        recent_bookings = db.query(Booking).order_by(
            Booking.created_at.desc()
        ).limit(5).all()
        
        for booking in recent_bookings:
            activities.append({
                "id": f"booking_{booking.id}",
                "type": "booking",
                "message": f"New booking created for {booking.vehicle.make} {booking.vehicle.model}" if booking.vehicle else f"New booking created (ID: {booking.id})",
                "timestamp": booking.created_at,
                "user": f"{booking.user.first_name} {booking.user.last_name}" if booking.user else "Unknown",
                "status": "success" if booking.status == "confirmed" else "info"
            })
        
        # Recent user registrations
        recent_users = db.query(User).order_by(
            User.created_at.desc()
        ).limit(3).all()
        
        for user in recent_users:
            activities.append({
                "id": f"user_{user.id}",
                "type": "user",
                "message": "New user registered",
                "timestamp": user.created_at,
                "user": f"{user.first_name} {user.last_name}",
                "status": "info"
            })
        
        # Recent payments
        recent_payments = db.query(Payment).order_by(
            Payment.created_at.desc()
        ).limit(3).all()
        
        for payment in recent_payments:
            activities.append({
                "id": f"payment_{payment.id}",
                "type": "payment",
                "message": f"Payment received for booking #{payment.booking_id}",
                "timestamp": payment.created_at,
                "user": f"{payment.booking.user.first_name} {payment.booking.user.last_name}" if payment.booking and payment.booking.user else "Unknown",
                "status": "success" if payment.status == "completed" else "warning"
            })
        
        # Sort all activities by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Take only the requested limit
        activities = activities[:limit]
        
        # Format timestamps for frontend
        for activity in activities:
            timestamp = activity["timestamp"]
            now = datetime.now()
            diff = now - timestamp
            
            if diff.days > 0:
                activity["timestamp"] = f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                activity["timestamp"] = f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                activity["timestamp"] = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                activity["timestamp"] = "Just now"
        
        return {"activities": activities}
        
    except Exception as e:
        return {"activities": [], "error": str(e)}
