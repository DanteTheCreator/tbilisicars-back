-- Rollback: Revert rate tiers from vehicle_model back to vehicle_group

-- Step 1: Add vehicle_group_id column back
ALTER TABLE ratetier ADD COLUMN vehicle_group_id INTEGER REFERENCES vehiclegroup(id) ON DELETE CASCADE;

-- Step 2: Migrate data back - map vehicle_model_id to vehicle_group_id via vehicle table
UPDATE ratetier rt
SET vehicle_group_id = (
    SELECT DISTINCT v.vehicle_group_id
    FROM vehicle v
    WHERE v.vehicle_model_id = rt.vehicle_model_id
      AND v.vehicle_group_id IS NOT NULL
    LIMIT 1
)
WHERE rt.vehicle_model_id IS NOT NULL;

-- Step 3: Remove new column and index
DROP INDEX IF EXISTS idx_ratetier_vehicle_model;
ALTER TABLE ratetier DROP COLUMN vehicle_model_id;

-- Step 4: Recreate old index
CREATE INDEX IF NOT EXISTS idx_ratetier_vehicle_group ON ratetier(vehicle_group_id);
