-- Add additional fields to maintenance_services table
ALTER TABLE maintenance_services
ADD COLUMN IF NOT EXISTS pickup_date VARCHAR(50),
ADD COLUMN IF NOT EXISTS dropoff_date VARCHAR(50),
ADD COLUMN IF NOT EXISTS branch_office VARCHAR(100),
ADD COLUMN IF NOT EXISTS location VARCHAR(100),
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Add comments
COMMENT ON COLUMN maintenance_services.pickup_date IS 'Pickup datetime';
COMMENT ON COLUMN maintenance_services.dropoff_date IS 'Drop-off datetime';
