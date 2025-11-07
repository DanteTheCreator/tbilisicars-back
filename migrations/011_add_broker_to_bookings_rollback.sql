-- Rollback: Remove broker field from bookings table

DROP INDEX IF EXISTS idx_booking_broker;
ALTER TABLE booking DROP COLUMN IF EXISTS broker;
