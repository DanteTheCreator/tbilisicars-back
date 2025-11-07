-- Rollback: Remove vehicle_group_id from booking table
DROP INDEX IF EXISTS idx_booking_vehicle_group_id;
ALTER TABLE booking DROP COLUMN IF EXISTS vehicle_group_id;
