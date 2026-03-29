-- Remove source column from booking table
DROP INDEX IF EXISTS ix_booking_source;
ALTER TABLE booking DROP COLUMN IF EXISTS source;
