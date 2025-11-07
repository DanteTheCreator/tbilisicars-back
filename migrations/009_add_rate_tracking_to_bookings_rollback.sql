-- Rollback: Remove rate tracking columns from bookings table

-- Remove indexes
DROP INDEX IF EXISTS idx_booking_rate_tier_id;
DROP INDEX IF EXISTS idx_booking_rate_id;

-- Remove columns
ALTER TABLE booking DROP COLUMN IF EXISTS price_per_day;
ALTER TABLE booking DROP COLUMN IF EXISTS rate_tier_id;
ALTER TABLE booking DROP COLUMN IF EXISTS rate_id;
