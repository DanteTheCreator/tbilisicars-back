-- Rollback: Remove starting_price column from vehicles

DROP INDEX IF EXISTS idx_vehicle_starting_price;
ALTER TABLE vehicle DROP COLUMN IF EXISTS starting_price;
