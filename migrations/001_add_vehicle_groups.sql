-- Migration: Add vehicle_groups table and update vehicle table
-- This migration creates the vehicle groups feature allowing vehicles to be organized into groups

-- Create vehicle_groups table
CREATE TABLE IF NOT EXISTS vehiclegroup (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    seats INTEGER,
    doors INTEGER,
    transmission VARCHAR(20),
    fuel_type VARCHAR(20),
    base_price_per_day NUMERIC(10, 2),
    base_price_per_week NUMERIC(10, 2),
    base_price_per_month NUMERIC(10, 2),
    features TEXT,
    image_url VARCHAR(500),
    display_order INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    min_rental_days INTEGER DEFAULT 1,
    max_rental_days INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for vehicle_groups
CREATE INDEX IF NOT EXISTS idx_vehiclegroup_name ON vehiclegroup(name);
CREATE INDEX IF NOT EXISTS idx_vehiclegroup_active ON vehiclegroup(active);

-- Add vehicle_group_id column to vehicle table
ALTER TABLE vehicle 
ADD COLUMN IF NOT EXISTS vehicle_group_id INTEGER;

-- Add foreign key constraint
ALTER TABLE vehicle 
ADD CONSTRAINT fk_vehicle_vehicle_group 
FOREIGN KEY (vehicle_group_id) 
REFERENCES vehiclegroup(id) 
ON DELETE SET NULL;

-- Create index on vehicle_group_id
CREATE INDEX IF NOT EXISTS idx_vehicle_vehicle_group_id ON vehicle(vehicle_group_id);

-- Add trigger to update updated_at timestamp for vehiclegroup table
CREATE OR REPLACE FUNCTION update_vehiclegroup_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vehiclegroup_updated_at
    BEFORE UPDATE ON vehiclegroup
    FOR EACH ROW
    EXECUTE FUNCTION update_vehiclegroup_updated_at();
