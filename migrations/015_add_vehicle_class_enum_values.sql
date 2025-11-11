-- Clean up and recreate vehicleclassenum enum with all required values

-- First, update any lowercase values to uppercase
UPDATE vehicle SET vehicle_class = 'STANDARD' WHERE vehicle_class = 'standard';
UPDATE vehicle SET vehicle_class = 'PREMIUM' WHERE vehicle_class = 'premium';
UPDATE vehicle SET vehicle_class = 'MINIVAN' WHERE vehicle_class = 'minivan';

-- Create a new clean enum type with all values
CREATE TYPE vehicleclassenum_new AS ENUM (
    'ECONOMY',
    'COMPACT', 
    'MIDSIZE',
    'STANDARD',
    'FULLSIZE',
    'PREMIUM',
    'LUXURY',
    'SUV',
    'MINIVAN',
    'VAN',
    'TRUCK'
);

-- Alter the vehicle table to use the new enum
ALTER TABLE vehicle 
    ALTER COLUMN vehicle_class TYPE vehicleclassenum_new 
    USING vehicle_class::text::vehicleclassenum_new;

-- Drop the old enum
DROP TYPE vehicleclassenum CASCADE;

-- Rename the new enum to the original name
ALTER TYPE vehicleclassenum_new RENAME TO vehicleclassenum;
