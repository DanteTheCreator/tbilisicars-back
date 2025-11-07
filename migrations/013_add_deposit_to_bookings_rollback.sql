-- Remove deposit column from bookings table
ALTER TABLE booking DROP COLUMN IF EXISTS deposit;
