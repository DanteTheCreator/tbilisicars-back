-- Rollback migration: Revert promotions back to code-based system
-- Date: 2025-10-27

BEGIN;

-- Update discount_type values back to lowercase
UPDATE promo SET discount_type = 'percent' WHERE discount_type = 'PERCENT';
UPDATE promo SET discount_type = 'fixed' WHERE discount_type = 'FIXED';

-- Revert enum to lowercase
ALTER TYPE discounttypeenum RENAME TO discounttypeenum_old;
CREATE TYPE discounttypeenum AS ENUM ('percent', 'fixed');
ALTER TABLE promo ALTER COLUMN discount_type TYPE discounttypeenum USING discount_type::text::discounttypeenum;
DROP TYPE discounttypeenum_old;

-- Make code column NOT NULL again (you may need to populate codes first)
-- ALTER TABLE promo ALTER COLUMN code SET NOT NULL;

-- Re-add unique constraint on code
-- ALTER TABLE promo ADD CONSTRAINT promo_code_key UNIQUE (code);

-- Drop index on vehicle_group_id
DROP INDEX IF EXISTS ix_promo_vehicle_group_id;

-- Drop foreign key constraint
ALTER TABLE promo DROP CONSTRAINT IF EXISTS fk_promo_vehicle_group;

-- Drop vehicle_group_id column
ALTER TABLE promo DROP COLUMN IF EXISTS vehicle_group_id;

COMMIT;
