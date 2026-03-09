-- Migration to change GASOLINE to PETROL in fueltypeenum

-- Step 1: Add PETROL to the enum
ALTER TYPE fueltypeenum ADD VALUE IF NOT EXISTS 'PETROL';

-- Step 2: Update all existing records
UPDATE vehicle SET fuel_type = 'PETROL' WHERE fuel_type = 'GASOLINE';

-- Step 3: Remove GASOLINE from enum (requires recreating the enum)
-- First create a temporary type
CREATE TYPE fueltypeenum_new AS ENUM ('PETROL', 'DIESEL', 'HYBRID', 'ELECTRIC');

-- Alter the column to use the new type
ALTER TABLE vehicle 
  ALTER COLUMN fuel_type TYPE fueltypeenum_new 
  USING fuel_type::text::fueltypeenum_new;

-- Drop the old type and rename the new one
DROP TYPE fueltypeenum;
ALTER TYPE fueltypeenum_new RENAME TO fueltypeenum;
