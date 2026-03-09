-- Rollback Migration 024: Remove model photo support from vehiclephoto

-- Drop constraint
ALTER TABLE vehiclephoto DROP CONSTRAINT IF EXISTS chk_vehiclephoto_owner;

-- Remove index
DROP INDEX IF EXISTS idx_vehiclephoto_model_id;

-- Remove column
ALTER TABLE vehiclephoto DROP COLUMN IF EXISTS vehicle_model_id;

-- Make vehicle_id required again
UPDATE vehiclephoto SET vehicle_id = 0 WHERE vehicle_id IS NULL;  -- Placeholder for orphaned photos
ALTER TABLE vehiclephoto ALTER COLUMN vehicle_id SET NOT NULL;
