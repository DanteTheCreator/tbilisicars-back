-- Migration: Update promotions to link to vehicle groups instead of codes
-- Date: 2025-10-27

BEGIN;

-- Add vehicle_group_id column to promo table
ALTER TABLE promo ADD COLUMN vehicle_group_id INTEGER;

-- Add foreign key constraint
ALTER TABLE promo 
    ADD CONSTRAINT fk_promo_vehicle_group 
    FOREIGN KEY (vehicle_group_id) 
    REFERENCES vehiclegroup(id) 
    ON DELETE CASCADE;

-- Add index on vehicle_group_id
CREATE INDEX ix_promo_vehicle_group_id ON promo(vehicle_group_id);

-- Remove the unique constraint on code column
ALTER TABLE promo DROP CONSTRAINT IF EXISTS promo_code_key;

-- Make code column nullable (for backwards compatibility during transition)
ALTER TABLE promo ALTER COLUMN code DROP NOT NULL;

-- Update discount type enum to use uppercase
ALTER TYPE discounttypeenum RENAME TO discounttypeenum_old;
CREATE TYPE discounttypeenum AS ENUM ('PERCENT', 'FIXED');

-- Update the column to use the new enum
ALTER TABLE promo ALTER COLUMN discount_type TYPE discounttypeenum USING discount_type::text::discounttypeenum;

-- Drop the old enum
DROP TYPE discounttypeenum_old;

-- Update existing discount_type values to uppercase
UPDATE promo SET discount_type = 'PERCENT' WHERE discount_type::text = 'percent';
UPDATE promo SET discount_type = 'FIXED' WHERE discount_type::text = 'fixed';

COMMIT;
