-- Add admin_id column to maintenance_services table
ALTER TABLE maintenance_services 
ADD COLUMN admin_id INTEGER REFERENCES admins(id) ON DELETE SET NULL;

-- Create index for better query performance
CREATE INDEX idx_maintenance_services_admin_id ON maintenance_services(admin_id);
