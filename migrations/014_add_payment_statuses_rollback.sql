-- Note: PostgreSQL does not support removing enum values directly.
-- To rollback, you would need to:
-- 1. Update all bookings with HALF or PREPAID status to another status
-- 2. Create a new enum type without these values
-- 3. Alter the column to use the new type
-- 4. Drop the old type

-- This is a destructive operation and should be done carefully in production.
-- For development, you can drop and recreate the entire enum.

-- Example rollback (destructive):
-- UPDATE booking SET payment_status = 'PARTIAL' WHERE payment_status IN ('HALF', 'PREPAID');
-- This migration is not easily reversible.
