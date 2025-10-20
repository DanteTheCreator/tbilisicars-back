-- Rollback Migration: Remove vehicle_groups table and related changes
-- This rollback script reverses the changes made by 001_add_vehicle_groups.sql

-- Drop the trigger first
DROP TRIGGER IF EXISTS trigger_update_vehiclegroup_updated_at ON vehiclegroup;
DROP FUNCTION IF EXISTS update_vehiclegroup_updated_at();

-- Remove the foreign key constraint from vehicle table
ALTER TABLE vehicle 
DROP CONSTRAINT IF EXISTS fk_vehicle_vehicle_group;

-- Drop the index on vehicle_group_id
DROP INDEX IF EXISTS idx_vehicle_vehicle_group_id;

-- Remove the vehicle_group_id column from vehicle table
ALTER TABLE vehicle 
DROP COLUMN IF EXISTS vehicle_group_id;

-- Drop indexes for vehicle_groups
DROP INDEX IF EXISTS idx_vehiclegroup_active;
DROP INDEX IF EXISTS idx_vehiclegroup_name;

-- Drop the vehiclegroup table
DROP TABLE IF EXISTS vehiclegroup;
