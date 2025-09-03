from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.vehicle import Vehicle
from app.models.booking import Booking
from app.models.user import User
from app.models.payment import Payment

router = APIRouter()

@router.get("/admin/reports")
async def get_reports(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
    range_days: int = Query(30, alias="range"),
    type: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Get aggregated report data for admin dashboard
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=range_days)
        
        # Bookings data
        total_bookings = db.query(Booking).filter(
            Booking.created_at >= start_date
        ).count()
        
        confirmed_bookings = db.query(Booking).filter(
            and_(
                Booking.created_at >= start_date,
                Booking.status == 'confirmed'
            )
        ).count()
        
        canceled_bookings = db.query(Booking).filter(
            and_(
                Booking.created_at >= start_date,
                Booking.status == 'canceled'
            )
        ).count()
        
        # Revenue calculation
        total_revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.created_at >= start_date
        ).scalar() or 0
        
        # Previous period for growth calculation
        prev_start = start_date - timedelta(days=range_days)
        prev_revenue = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.created_at >= prev_start,
                Payment.created_at < start_date
            )
        ).scalar() or 0
        
        revenue_growth = 0
        if prev_revenue > 0:
            revenue_growth = ((total_revenue - prev_revenue) / prev_revenue) * 100
        
        # Vehicle data
        total_vehicles = db.query(Vehicle).count()
        available_vehicles = db.query(Vehicle).filter(
            Vehicle.status == 'available'
        ).count()
        rented_vehicles = db.query(Vehicle).filter(
            Vehicle.status == 'rented'
        ).count()
        
        utilization = (rented_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        
        # Customer data
        total_customers = db.query(User).count()
        new_customers = db.query(User).filter(
            User.created_at >= start_date
        ).count()
        
        # Popular vehicles (top 5 by bookings)
        popular_vehicles_query = db.query(
            Vehicle.id,
            Vehicle.make,
            Vehicle.model,
            func.count(Booking.id).label('booking_count'),
            func.sum(Booking.total_amount).label('total_revenue')
        ).join(
            Booking, Vehicle.id == Booking.vehicle_id
        ).filter(
            Booking.created_at >= start_date
        ).group_by(
            Vehicle.id, Vehicle.make, Vehicle.model
        ).order_by(
            func.count(Booking.id).desc()
        ).limit(5).all()
        
        popular_vehicles = [
            {
                "id": v.id,
                "make": v.make,
                "model": v.model,
                "bookings": v.booking_count,
                "revenue": float(v.total_revenue or 0)
            }
            for v in popular_vehicles_query
        ]
        
        # Monthly revenue data (last 12 months)
        monthly_data = []
        for i in range(12):
            month_start = end_date.replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_revenue = db.query(func.sum(Payment.amount)).filter(
                and_(
                    Payment.created_at >= month_start,
                    Payment.created_at <= month_end
                )
            ).scalar() or 0
            
            month_bookings = db.query(Booking).filter(
                and_(
                    Booking.created_at >= month_start,
                    Booking.created_at <= month_end
                )
            ).count()
            
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "revenue": float(month_revenue),
                "bookings": month_bookings
            })
        
        return {
            "bookings": {
                "total": total_bookings,
                "confirmed": confirmed_bookings,
                "canceled": canceled_bookings,
                "revenue": float(total_revenue),
                "growth": revenue_growth
            },
            "vehicles": {
                "total": total_vehicles,
                "available": available_vehicles,
                "rented": rented_vehicles,
                "utilization": utilization
            },
            "revenue": {
                "monthly": float(total_revenue),
                "weekly": float(total_revenue / 4),  # Approximate
                "daily": float(total_revenue / range_days),
                "growth": revenue_growth
            },
            "customers": {
                "total": total_customers,
                "new": new_customers,
                "returning": total_customers - new_customers,
                "growth": (new_customers / total_customers * 100) if total_customers > 0 else 0
            },
            "popular_vehicles": popular_vehicles,
            "monthly_revenue": list(reversed(monthly_data))
        }
        
    except Exception as e:
        return {
            "error": f"Failed to generate report: {str(e)}",
            "bookings": {"total": 0, "confirmed": 0, "canceled": 0, "revenue": 0, "growth": 0},
            "vehicles": {"total": 0, "available": 0, "rented": 0, "utilization": 0},
            "revenue": {"monthly": 0, "weekly": 0, "daily": 0, "growth": 0},
            "customers": {"total": 0, "new": 0, "returning": 0, "growth": 0},
            "popular_vehicles": [],
            "monthly_revenue": []
        }

@router.post("/admin/reports/generate")
async def generate_report(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Generate a custom report based on parameters
    """
    # This would implement custom report generation
    # For now, return a simple response
    return {
        "message": "Report generation initiated",
        "report_id": "12345",
        "status": "processing"
    }

@router.get("/admin/reports/export")
async def export_report(
    format: str = Query("json"),
    type: Optional[str] = Query(None),
    range_days: int = Query(30, alias="range"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Export reports in different formats
    """
    # Get the report data
    report_data = await get_reports(db=db, range_days=range_days, type=type)
    
    if format == "csv":
        # For CSV, we'd convert the data to CSV format
        # For now, return JSON with appropriate headers
        return report_data
    elif format == "pdf":
        # For PDF, we'd generate a PDF report
        # For now, return JSON with appropriate headers
        return report_data
    else:
        # Default JSON format
        return report_data
