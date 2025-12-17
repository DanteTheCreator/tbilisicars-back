-- Rollback: Remove broker_id from bookings table

DROP INDEX IF EXISTS ix_booking_broker_id;
ALTER TABLE booking DROP COLUMN IF EXISTS broker_id;
