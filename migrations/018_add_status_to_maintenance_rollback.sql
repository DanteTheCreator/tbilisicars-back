-- Rollback: Remove status column from maintenance_services table
ALTER TABLE maintenance_services DROP COLUMN status;
