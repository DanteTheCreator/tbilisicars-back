-- Rollback: Remove added vehicle class enum values
-- Note: PostgreSQL does not support removing enum values directly
-- This would require:
-- 1. Update all vehicles using these values to a different value
-- 2. Create a new enum without these values
-- 3. Alter the column to use the new enum
-- 4. Drop the old enum

-- For safety, this rollback is not destructive and just documents the process
-- If you need to remove these values, do it manually with care

/*
Example rollback process (USE WITH CAUTION):

-- 1. Update vehicles with new enum values to fallback values
UPDATE vehicle SET vehicle_class = 'economy' WHERE vehicle_class = 'standard';
UPDATE vehicle SET vehicle_class = 'luxury' WHERE vehicle_class = 'premium';
UPDATE vehicle SET vehicle_class = 'van' WHERE vehicle_class = 'minivan';

-- 2. Create new enum type without new values
CREATE TYPE vehicleclassenum_new AS ENUM ('economy', 'compact', 'midsize', 'fullsize', 'luxury', 'suv', 'van', 'truck');

-- 3. Alter column to use new type
ALTER TABLE vehicle ALTER COLUMN vehicle_class TYPE vehicleclassenum_new USING vehicle_class::text::vehicleclassenum_new;

-- 4. Drop old enum and rename new one
DROP TYPE vehicleclassenum;
ALTER TYPE vehicleclassenum_new RENAME TO vehicleclassenum;
*/

-- This migration added: 'standard', 'premium', 'minivan' to vehicleclassenum
