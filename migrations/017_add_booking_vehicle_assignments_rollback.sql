-- Rollback: Drop booking vehicle assignments table and related objects

DROP TRIGGER IF EXISTS trigger_update_booking_vehicle_assignments_updated_at ON booking_vehicle_assignments;

DROP FUNCTION IF EXISTS update_booking_vehicle_assignments_updated_at();

DROP INDEX IF EXISTS idx_booking_vehicle_assignments_dates;
DROP INDEX IF EXISTS idx_booking_vehicle_assignments_vehicle_id;
DROP INDEX IF EXISTS idx_booking_vehicle_assignments_booking_id;

DROP TABLE IF EXISTS booking_vehicle_assignments;
