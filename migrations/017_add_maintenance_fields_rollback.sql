-- Rollback: Remove additional fields from maintenance_services table
ALTER TABLE maintenance_services
DROP COLUMN IF EXISTS pickup_date,
DROP COLUMN IF EXISTS dropoff_date,
DROP COLUMN IF EXISTS branch_office,
DROP COLUMN IF EXISTS location,
DROP COLUMN IF EXISTS notes;
