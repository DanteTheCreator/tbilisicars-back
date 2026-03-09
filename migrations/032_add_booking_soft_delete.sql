-- Migration 032: Add soft-delete support to bookings
-- Adds deleted_at timestamp; bookings with a non-NULL deleted_at are considered deleted.
-- Physical deletion of booking rows is no longer performed.

ALTER TABLE booking ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;

CREATE INDEX IF NOT EXISTS ix_booking_deleted_at ON booking (deleted_at);
