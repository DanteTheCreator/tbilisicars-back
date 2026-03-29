from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, case, cast, Float, String, Date
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.booking import Booking
from app.models.maintenance import MaintenanceService

router = APIRouter()

# Helper: effective date for maintenance services (pickup_date is VARCHAR, created_at is TIMESTAMP)
# Cast created_at to VARCHAR so coalesce types match, then use cast to Date where needed
def _svc_date_str():
    """Returns a VARCHAR expression: pickup_date or created_at cast to string."""
    return func.coalesce(MaintenanceService.pickup_date, cast(MaintenanceService.created_at, String))

def _svc_date():
    """Returns a DATE expression from the effective service date."""
    return cast(_svc_date_str(), Date)


@router.get("/admin/finance/calendar")
async def get_finance_calendar(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Get daily income and expenses for a given month (calendar view).
    Income = booking total_amount (by pickup_datetime or created_at).
    Expenses = maintenance service cost (by pickup_date or service_date).
    """
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Daily income from bookings (grouped by pickup date)
    daily_income = (
        db.query(
            func.date(Booking.pickup_datetime).label("day"),
            Booking.currency,
            func.sum(Booking.total_amount).label("total"),
            func.count(Booking.id).label("count"),
        )
        .filter(
            Booking.pickup_datetime >= start_date,
            Booking.pickup_datetime < end_date,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .group_by(func.date(Booking.pickup_datetime), Booking.currency)
        .all()
    )

    # Daily expenses from maintenance services
    daily_expenses = (
        db.query(
            _svc_date().label("day"),
            func.sum(MaintenanceService.cost).label("total"),
            func.count(MaintenanceService.id).label("count"),
        )
        .filter(
            _svc_date() >= start_date.date(),
            _svc_date() < end_date.date(),
        )
        .group_by(_svc_date())
        .all()
    )

    # Build daily map
    days: Dict[str, Dict] = {}
    for row in daily_income:
        day_str = str(row.day)
        if day_str not in days:
            days[day_str] = {"income": {}, "expenses": 0, "booking_count": 0, "service_count": 0}
        currency = row.currency or "USD"
        days[day_str]["income"][currency] = float(row.total or 0)
        days[day_str]["booking_count"] += row.count

    for row in daily_expenses:
        day_str = str(row.day)
        if day_str not in days:
            days[day_str] = {"income": {}, "expenses": 0, "booking_count": 0, "service_count": 0}
        days[day_str]["expenses"] += float(row.total or 0)
        days[day_str]["service_count"] += row.count

    return {"year": year, "month": month, "days": days}


@router.get("/admin/finance/totals")
async def get_finance_totals(
    period: str = Query("month", regex="^(week|month|quarter|year|all)$"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Get aggregated finance totals for a given period.
    """
    now = datetime.now()
    if period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        prev_start = start - timedelta(days=7)
        prev_end = start
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = (start - timedelta(days=1)).replace(day=1)
        prev_end = start
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_quarter_month = quarter_month + 3
        if end_quarter_month > 12:
            end = now.replace(year=now.year + 1, month=end_quarter_month - 12, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(month=end_quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = (start - timedelta(days=1)).replace(day=1)
        prev_start = prev_start.replace(month=((prev_start.month - 1) // 3) * 3 + 1)
        prev_end = start
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = start.replace(year=start.year - 1)
        prev_end = start
    else:  # all
        start = datetime(2000, 1, 1)
        end = datetime(2100, 1, 1)
        prev_start = start
        prev_end = start

    # Current period income by currency
    income_rows = (
        db.query(
            Booking.currency,
            func.sum(Booking.total_amount).label("total"),
            func.count(Booking.id).label("count"),
        )
        .filter(
            Booking.pickup_datetime >= start,
            Booking.pickup_datetime < end,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .group_by(Booking.currency)
        .all()
    )

    income = {}
    total_bookings = 0
    for row in income_rows:
        currency = row.currency or "USD"
        income[currency] = float(row.total or 0)
        total_bookings += row.count

    # Previous period income (for growth)
    prev_income_total = (
        db.query(func.sum(Booking.total_amount))
        .filter(
            Booking.pickup_datetime >= prev_start,
            Booking.pickup_datetime < prev_end,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .scalar()
    ) or 0

    current_income_total = sum(income.values())
    income_growth = 0
    if float(prev_income_total) > 0:
        income_growth = ((current_income_total - float(prev_income_total)) / float(prev_income_total)) * 100

    # Current period expenses
    expenses_total = (
        db.query(func.sum(MaintenanceService.cost))
        .filter(_svc_date() >= start.date(), _svc_date() < end.date())
        .scalar()
    ) or 0

    total_services = (
        db.query(func.count(MaintenanceService.id))
        .filter(_svc_date() >= start.date(), _svc_date() < end.date())
        .scalar()
    ) or 0

    # Previous period expenses
    prev_expenses_total = (
        db.query(func.sum(MaintenanceService.cost))
        .filter(
            _svc_date() >= prev_start.date(),
            _svc_date() < prev_end.date(),
        )
        .scalar()
    ) or 0

    expenses_growth = 0
    if float(prev_expenses_total) > 0:
        expenses_growth = ((float(expenses_total) - float(prev_expenses_total)) / float(prev_expenses_total)) * 100

    # Payment status breakdown
    payment_breakdown = (
        db.query(
            Booking.payment_status,
            func.count(Booking.id).label("count"),
            func.sum(Booking.total_amount).label("total"),
        )
        .filter(
            Booking.pickup_datetime >= start,
            Booking.pickup_datetime < end,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .group_by(Booking.payment_status)
        .all()
    )

    payment_statuses = {}
    for row in payment_breakdown:
        status = row.payment_status or "UNPAID"
        payment_statuses[status] = {
            "count": row.count,
            "total": float(row.total or 0),
        }

    # Average booking value by currency
    avg_booking = (
        db.query(
            Booking.currency,
            func.avg(Booking.total_amount).label("avg"),
        )
        .filter(
            Booking.pickup_datetime >= start,
            Booking.pickup_datetime < end,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .group_by(Booking.currency)
        .all()
    )

    avg_booking_value = {}
    for row in avg_booking:
        currency = row.currency or "USD"
        avg_booking_value[currency] = round(float(row.avg or 0), 2)

    # Monthly breakdown (last 6 months)
    six_months_ago = (now - timedelta(days=180)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_income = (
        db.query(
            extract("year", Booking.pickup_datetime).label("yr"),
            extract("month", Booking.pickup_datetime).label("mn"),
            Booking.currency,
            func.sum(Booking.total_amount).label("total"),
        )
        .filter(
            Booking.pickup_datetime >= six_months_ago,
            Booking.status.notin_(["CANCELED", "NO_SHOW"]),
        )
        .group_by("yr", "mn", Booking.currency)
        .order_by("yr", "mn")
        .all()
    )

    monthly_data: Dict[str, Dict] = {}
    for row in monthly_income:
        key = f"{int(row.yr)}-{int(row.mn):02d}"
        if key not in monthly_data:
            monthly_data[key] = {"income": {}, "expenses": 0}
        currency = row.currency or "USD"
        monthly_data[key]["income"][currency] = float(row.total or 0)

    monthly_expenses = (
        db.query(
            extract("year", _svc_date()).label("yr"),
            extract("month", _svc_date()).label("mn"),
            func.sum(MaintenanceService.cost).label("total"),
        )
        .filter(_svc_date() >= six_months_ago.date())
        .group_by("yr", "mn")
        .order_by("yr", "mn")
        .all()
    )

    for row in monthly_expenses:
        key = f"{int(row.yr)}-{int(row.mn):02d}"
        if key not in monthly_data:
            monthly_data[key] = {"income": {}, "expenses": 0}
        monthly_data[key]["expenses"] = float(row.total or 0)

    return {
        "period": period,
        "income": income,
        "income_total": current_income_total,
        "income_growth": round(income_growth, 2),
        "expenses_total": float(expenses_total),
        "expenses_growth": round(expenses_growth, 2),
        "net_profit": current_income_total - float(expenses_total),
        "total_bookings": total_bookings,
        "total_services": total_services,
        "payment_statuses": payment_statuses,
        "avg_booking_value": avg_booking_value,
        "monthly_data": monthly_data,
    }
