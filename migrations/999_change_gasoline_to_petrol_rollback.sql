-- Rollback migration: change PETROL back to GASOLINE in fueltypeenum

-- Step 1: Create new enum with GASOLINE
CREATE TYPE fueltypeenum_new AS ENUM ('GASOLINE', 'DIESEL', 'HYBRID', 'ELECTRIC');

-- Step 2: Update all existing records from PETROL to GASOLINE
UPDATE vehicle SET fuel_type = 'GASOLINE' WHERE fuel_type = 'PETROL';

-- Step 3: Alter the column to use the new type
ALTER TABLE vehicle 
  ALTER COLUMN fuel_type TYPE fueltypeenum_new 
  USING fuel_type::text::fueltypeenum_new;

-- Step 4: Drop the old type and rename the new one
DROP TYPE fueltypeenum;
ALTER TYPE fueltypeenum_new RENAME TO fueltypeenum;
