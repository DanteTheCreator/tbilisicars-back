-- Rollback Migration 023: Remove Brand and VehicleModel tables

-- First, ensure legacy make/model fields are populated from vehicle_model
UPDATE vehicle v
SET 
    make = b.name,
    model = vm.name
FROM vehicle_model vm
JOIN brand b ON b.id = vm.brand_id
WHERE v.vehicle_model_id = vm.id
AND v.make IS NULL;

-- Make make and model required again
ALTER TABLE vehicle ALTER COLUMN make SET NOT NULL;
ALTER TABLE vehicle ALTER COLUMN model SET NOT NULL;

-- Drop foreign key column
DROP INDEX IF EXISTS idx_vehicle_model_id;
ALTER TABLE vehicle DROP COLUMN IF EXISTS vehicle_model_id;

-- Drop tables in reverse order due to foreign keys
DROP TABLE IF EXISTS vehicle_model CASCADE;
DROP TABLE IF EXISTS brand CASCADE;
