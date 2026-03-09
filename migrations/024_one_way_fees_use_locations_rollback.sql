-- Rollback: Revert one_way_fees from location FKs back to city strings

-- Drop new constraints and indexes
ALTER TABLE one_way_fees DROP CONSTRAINT IF EXISTS uq_one_way_fee_locations;
DROP INDEX IF EXISTS idx_one_way_fees_from_location;
DROP INDEX IF EXISTS idx_one_way_fees_to_location;
ALTER TABLE one_way_fees DROP CONSTRAINT IF EXISTS fk_one_way_fees_from_location;
ALTER TABLE one_way_fees DROP CONSTRAINT IF EXISTS fk_one_way_fees_to_location;

-- Drop new columns
ALTER TABLE one_way_fees DROP COLUMN IF EXISTS from_location_id;
ALTER TABLE one_way_fees DROP COLUMN IF EXISTS to_location_id;

-- Re-add old columns
ALTER TABLE one_way_fees ADD COLUMN from_city VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE one_way_fees ADD COLUMN to_city VARCHAR(100) NOT NULL DEFAULT '';

-- Re-add old constraints
ALTER TABLE one_way_fees ADD CONSTRAINT uq_one_way_fee_cities UNIQUE (from_city, to_city);
CREATE INDEX idx_one_way_fees_cities ON one_way_fees(from_city, to_city);
