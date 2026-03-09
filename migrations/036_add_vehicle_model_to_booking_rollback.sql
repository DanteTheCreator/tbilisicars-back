-- Rollback Migration 036: Remove vehicle_model_id from booking table

DROP INDEX IF EXISTS idx_booking_vehicle_model_id;
ALTER TABLE booking DROP CONSTRAINT IF EXISTS fk_booking_vehicle_model;
ALTER TABLE booking DROP COLUMN IF EXISTS vehicle_model_id;
