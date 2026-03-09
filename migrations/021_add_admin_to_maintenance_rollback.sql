-- Rollback: Remove admin_id column
DROP INDEX IF EXISTS idx_maintenance_services_admin_id;
ALTER TABLE maintenance_services DROP COLUMN admin_id;
