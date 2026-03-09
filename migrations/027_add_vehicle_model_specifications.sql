-- Migration 027: Add specifications and pricing fields to vehicle_model table
-- Adds fields for external system integration, category, pricing, and vehicle specs

-- Add external system availability flag
ALTER TABLE vehicle_model ADD COLUMN available_for_external_systems BOOLEAN NOT NULL DEFAULT FALSE;

-- Add category field (e.g., Economy, Standard, SUV, Luxury, etc.)
ALTER TABLE vehicle_model ADD COLUMN category VARCHAR(100);

-- Add pricing fields
ALTER TABLE vehicle_model ADD COLUMN price NUMERIC(10, 2);  -- Default/base price
ALTER TABLE vehicle_model ADD COLUMN price_gel NUMERIC(10, 2);  -- Price in GEL
ALTER TABLE vehicle_model ADD COLUMN price_usd NUMERIC(10, 2);  -- Price in USD

-- Add vehicle specifications
ALTER TABLE vehicle_model ADD COLUMN passengers INTEGER;
ALTER TABLE vehicle_model ADD COLUMN large_suitcases INTEGER;
ALTER TABLE vehicle_model ADD COLUMN small_suitcases INTEGER;
ALTER TABLE vehicle_model ADD COLUMN doors INTEGER;

-- Add fuel information
ALTER TABLE vehicle_model ADD COLUMN fuel_type VARCHAR(50);  -- Gasoline, Diesel, Electric, Hybrid
ALTER TABLE vehicle_model ADD COLUMN fuel_tank_size INTEGER;  -- Fuel tank size in liters

-- Add indexes for commonly queried fields
CREATE INDEX idx_vehicle_model_category ON vehicle_model(category);
CREATE INDEX idx_vehicle_model_fuel_type ON vehicle_model(fuel_type);
CREATE INDEX idx_vehicle_model_available_external ON vehicle_model(available_for_external_systems);

-- Add comments for documentation
COMMENT ON COLUMN vehicle_model.available_for_external_systems IS 'Whether this model is available for external booking systems';
COMMENT ON COLUMN vehicle_model.category IS 'Vehicle category (Economy, Standard, SUV, Luxury, etc.)';
COMMENT ON COLUMN vehicle_model.price IS 'Default/base price for the vehicle model';
COMMENT ON COLUMN vehicle_model.price_gel IS 'Price in Georgian Lari (GEL)';
COMMENT ON COLUMN vehicle_model.price_usd IS 'Price in US Dollars (USD)';
COMMENT ON COLUMN vehicle_model.passengers IS 'Number of passengers the vehicle can accommodate';
COMMENT ON COLUMN vehicle_model.large_suitcases IS 'Number of large suitcases that fit in the trunk';
COMMENT ON COLUMN vehicle_model.small_suitcases IS 'Number of small suitcases that fit in the trunk';
COMMENT ON COLUMN vehicle_model.doors IS 'Number of doors';
COMMENT ON COLUMN vehicle_model.fuel_type IS 'Type of fuel (Gasoline, Diesel, Electric, Hybrid)';
COMMENT ON COLUMN vehicle_model.fuel_tank_size IS 'Fuel tank capacity in liters';
