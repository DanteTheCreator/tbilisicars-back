from __future__ import annotations

from fastapi import APIRouter

# Import individual resource routers
from .auth import router as auth_router
from .users import router as users_router
from .locations import router as locations_router
from .vehicles import router as vehicles_router
from .vehicle_groups import router as vehicle_groups_router
from .vehicle_prices import router as vehicle_prices_router
from .vehicle_photos import router as vehicle_photos_router
from .booking_photos import router as booking_photos_router
from .bookings import router as bookings_router
from .extras import router as extras_router
from .booking_extras import router as booking_extras_router
from .payments import router as payments_router
from .damages import router as damages_router
from .promos import router as promos_router
from .booking_promos import router as booking_promos_router
from .reviews import router as reviews_router
from .documents import router as documents_router
from .rates import router as rates_router
from .admin_stats import router as admin_stats_router
from .admin_reports import router as admin_reports_router
from .admin_settings import router as admin_settings_router
from .admin_management import router as admin_management_router
from .one_way_fees import router as one_way_fees_router
from .booking_emails import router as booking_emails_router
from .email_bookings import router as email_bookings_router
from .tasks import router as tasks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(locations_router)
api_router.include_router(vehicles_router)
api_router.include_router(vehicle_groups_router)
api_router.include_router(vehicle_prices_router)
api_router.include_router(vehicle_photos_router)
api_router.include_router(bookings_router)
api_router.include_router(booking_photos_router)
api_router.include_router(extras_router)
api_router.include_router(booking_extras_router)
api_router.include_router(payments_router)
api_router.include_router(damages_router)
api_router.include_router(promos_router)
api_router.include_router(booking_promos_router)
api_router.include_router(reviews_router)
api_router.include_router(documents_router)
api_router.include_router(rates_router)
api_router.include_router(admin_stats_router)
api_router.include_router(admin_reports_router)
api_router.include_router(admin_settings_router)
api_router.include_router(admin_management_router)
api_router.include_router(one_way_fees_router)
api_router.include_router(email_bookings_router)
api_router.include_router(tasks_router)
