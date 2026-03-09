-- Rollback Migration 027: Remove specifications and pricing fields from vehicle_model table

-- Drop indexes
DROP INDEX IF EXISTS idx_vehicle_model_category;
DROP INDEX IF EXISTS idx_vehicle_model_fuel_type;
DROP INDEX IF EXISTS idx_vehicle_model_available_external;

-- Remove columns
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS available_for_external_systems;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS category;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price_gel;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price_usd;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS passengers;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS large_suitcases;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS small_suitcases;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS doors;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS fuel_type;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS fuel_tank_size;
