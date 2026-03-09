-- Rollback: remove pricing_type column from extra table
ALTER TABLE extra DROP COLUMN IF EXISTS pricing_type;
DROP TYPE IF EXISTS extrapricingtypeenum;
