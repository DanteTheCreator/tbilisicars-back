-- Rollback one_way_fees table
DROP INDEX IF EXISTS idx_one_way_fees_cities;
DROP TABLE IF EXISTS one_way_fees;

-- Remove one_way_fee field from bookings table
ALTER TABLE bookings DROP COLUMN IF EXISTS one_way_fee;
