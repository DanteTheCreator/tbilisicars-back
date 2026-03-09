"""Background service to auto-archive completed bookings after 24 hours."""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.booking import Booking, BookingStatusEnum

logger = logging.getLogger(__name__)

# Statuses considered "completed" — eligible for auto-archiving
ARCHIVABLE_STATUSES = (
    BookingStatusEnum.RETURNED,
    BookingStatusEnum.CANCELED,
    BookingStatusEnum.NO_SHOW,
)

# How long after the last update before a booking is archived
ARCHIVE_AFTER_HOURS = 24

# How often the archiver checks (in seconds) — defaults to every hour
DEFAULT_CHECK_INTERVAL = 3600


class BookingArchiverService:
    """Periodically soft-deletes completed bookings older than 24 h."""

    def __init__(self, check_interval: int = DEFAULT_CHECK_INTERVAL):
        self.check_interval = check_interval
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        if self.is_running:
            logger.warning("Booking archiver already running")
            return
        logger.info("Starting booking archiver service (interval=%ss)", self.check_interval)
        self.is_running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        logger.info("Stopping booking archiver service")
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while self.is_running:
            try:
                archived = self._archive_completed_bookings()
                if archived:
                    logger.info("Auto-archived %d completed booking(s)", archived)
            except Exception:
                logger.exception("Error in booking archiver")

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    # ── core logic (sync, runs inside its own DB session) ──────────
    @staticmethod
    def _archive_completed_bookings() -> int:
        db: Session = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=ARCHIVE_AFTER_HOURS)

            bookings = (
                db.query(Booking)
                .filter(
                    Booking.status.in_(ARCHIVABLE_STATUSES),
                    Booking.deleted_at.is_(None),
                    Booking.updated_at <= cutoff,
                )
                .all()
            )

            now = datetime.utcnow()
            for booking in bookings:
                booking.deleted_at = now
                logger.debug(
                    "Archiving booking #%d (status=%s, updated_at=%s)",
                    booking.id,
                    booking.status,
                    booking.updated_at,
                )

            db.commit()
            return len(bookings)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Global singleton — imported in main.py
booking_archiver_service = BookingArchiverService()
