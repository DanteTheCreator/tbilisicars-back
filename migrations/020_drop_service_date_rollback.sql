-- Rollback: Add service_date column back
ALTER TABLE maintenance_services ADD COLUMN service_date DATE;
