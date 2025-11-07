-- Rollback: Remove delivery_fee column from bookings table
ALTER TABLE booking DROP COLUMN IF EXISTS delivery_fee;
