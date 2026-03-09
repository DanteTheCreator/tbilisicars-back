-- Rollback 032: Remove soft-delete column from bookings

DROP INDEX IF EXISTS ix_booking_deleted_at;

ALTER TABLE booking DROP COLUMN IF EXISTS deleted_at;
