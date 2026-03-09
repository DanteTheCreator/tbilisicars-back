-- Rollback: Make service_date NOT NULL again
ALTER TABLE maintenance_services 
ALTER COLUMN service_date SET NOT NULL;
