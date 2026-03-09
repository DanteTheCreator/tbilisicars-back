-- Migration: Change rate tiers from vehicle_group to vehicle_model
-- Rate pricing is now set per vehicle model instead of per vehicle group/category

-- Step 1: Add vehicle_model_id column to ratetier (nullable initially)
ALTER TABLE ratetier ADD COLUMN vehicle_model_id INTEGER REFERENCES vehicle_model(id) ON DELETE CASCADE;

-- Step 2: Expand existing tiers - for each tier's vehicle_group_id,
-- create a copy for every vehicle_model that belongs to that group.
-- We insert new rows for all models (except the first one per group, which we'll UPDATE onto the original row).
-- First: insert additional rows for 2nd+ models in each group
INSERT INTO ratetier (rate_id, vehicle_model_id, from_days, to_days, price_per_day, currency, created_at, updated_at)
SELECT rt.rate_id, v.vehicle_model_id, rt.from_days, rt.to_days, rt.price_per_day, rt.currency, NOW(), NOW()
FROM ratetier rt
JOIN (
    SELECT DISTINCT vehicle_group_id, vehicle_model_id,
           ROW_NUMBER() OVER (PARTITION BY vehicle_group_id ORDER BY vehicle_model_id) as rn
    FROM vehicle
    WHERE vehicle_model_id IS NOT NULL AND vehicle_group_id IS NOT NULL
) v ON v.vehicle_group_id = rt.vehicle_group_id AND v.rn > 1
WHERE rt.vehicle_group_id IS NOT NULL;

-- Then: update original rows to point to the first model in each group
UPDATE ratetier rt
SET vehicle_model_id = (
    SELECT DISTINCT v.vehicle_model_id
    FROM vehicle v
    WHERE v.vehicle_group_id = rt.vehicle_group_id
      AND v.vehicle_model_id IS NOT NULL
    ORDER BY v.vehicle_model_id
    LIMIT 1
)
WHERE rt.vehicle_group_id IS NOT NULL AND rt.vehicle_model_id IS NULL;

-- Step 3: Delete tiers that couldn't be mapped (groups with no vehicles/models)
DELETE FROM ratetier WHERE vehicle_model_id IS NULL;

-- Step 4: Remove old column and index
DROP INDEX IF EXISTS idx_ratetier_vehicle_group;
ALTER TABLE ratetier DROP COLUMN vehicle_group_id;

-- Step 5: Create new index
CREATE INDEX IF NOT EXISTS idx_ratetier_vehicle_model ON ratetier(vehicle_model_id);
