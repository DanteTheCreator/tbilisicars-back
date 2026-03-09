-- Migration: Change one_way_fees from city strings to location foreign keys
-- This replaces from_city/to_city with from_location_id/to_location_id

-- Step 1: Add new columns
ALTER TABLE one_way_fees ADD COLUMN IF NOT EXISTS from_location_id INTEGER;
ALTER TABLE one_way_fees ADD COLUMN IF NOT EXISTS to_location_id INTEGER;

-- Step 2: Add foreign key constraints
ALTER TABLE one_way_fees
    ADD CONSTRAINT fk_one_way_fees_from_location
    FOREIGN KEY (from_location_id) REFERENCES location(id) ON DELETE CASCADE;

ALTER TABLE one_way_fees
    ADD CONSTRAINT fk_one_way_fees_to_location
    FOREIGN KEY (to_location_id) REFERENCES location(id) ON DELETE CASCADE;

-- Step 3: Drop old unique constraint and columns
ALTER TABLE one_way_fees DROP CONSTRAINT IF EXISTS uq_one_way_fee_cities;
DROP INDEX IF EXISTS idx_one_way_fees_cities;
ALTER TABLE one_way_fees DROP COLUMN IF EXISTS from_city;
ALTER TABLE one_way_fees DROP COLUMN IF EXISTS to_city;

-- Step 4: Make new columns NOT NULL (after dropping old data — existing rows will be deleted)
DELETE FROM one_way_fees;  -- Clear old city-based data

ALTER TABLE one_way_fees ALTER COLUMN from_location_id SET NOT NULL;
ALTER TABLE one_way_fees ALTER COLUMN to_location_id SET NOT NULL;

-- Step 5: Add new unique constraint and indexes
ALTER TABLE one_way_fees ADD CONSTRAINT uq_one_way_fee_locations UNIQUE (from_location_id, to_location_id);
CREATE INDEX IF NOT EXISTS idx_one_way_fees_from_location ON one_way_fees(from_location_id);
CREATE INDEX IF NOT EXISTS idx_one_way_fees_to_location ON one_way_fees(to_location_id);

-- Comment
COMMENT ON TABLE one_way_fees IS 'One-way rental fees between specific locations (e.g. Tbilisi Airport -> Batumi Downtown)';
