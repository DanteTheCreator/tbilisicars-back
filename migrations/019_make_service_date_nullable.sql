-- Make service_date nullable in maintenance_services table
ALTER TABLE maintenance_services 
ALTER COLUMN service_date DROP NOT NULL;
