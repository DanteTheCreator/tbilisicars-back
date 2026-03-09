-- Add status column to maintenance_services table
ALTER TABLE maintenance_services 
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Programmed';

-- Update existing records to have a default status
UPDATE maintenance_services 
SET status = 'Programmed' 
WHERE status IS NULL;
