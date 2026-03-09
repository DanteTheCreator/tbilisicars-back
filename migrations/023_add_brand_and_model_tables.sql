-- Migration 023: Add Brand and VehicleModel tables for hierarchical vehicle structure
-- This creates Brand -> Model -> Vehicle hierarchy

-- Create Brand table
CREATE TABLE brand (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    logo_url VARCHAR(500),
    country_of_origin VARCHAR(100),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_brand_name UNIQUE (name)
);

CREATE INDEX idx_brand_name ON brand(name);

-- Create VehicleModel table
CREATE TABLE vehicle_model (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brand(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_brand_model_name UNIQUE (brand_id, name)
);

CREATE INDEX idx_vehicle_model_brand_id ON vehicle_model(brand_id);
CREATE INDEX idx_vehicle_model_name ON vehicle_model(name);

-- Add vehicle_model_id to vehicle table
ALTER TABLE vehicle ADD COLUMN vehicle_model_id INTEGER REFERENCES vehicle_model(id) ON DELETE SET NULL;
CREATE INDEX idx_vehicle_model_id ON vehicle(vehicle_model_id);

-- Make legacy make and model fields nullable for backward compatibility
ALTER TABLE vehicle ALTER COLUMN make DROP NOT NULL;
ALTER TABLE vehicle ALTER COLUMN model DROP NOT NULL;

-- Migrate existing data: Create brands and models from existing vehicles
-- First, insert unique brands
INSERT INTO brand (name, active)
SELECT DISTINCT make, TRUE
FROM vehicle
WHERE make IS NOT NULL AND make != ''
ORDER BY make;

-- Then, insert unique models for each brand
INSERT INTO vehicle_model (brand_id, name, active)
SELECT b.id, v.model, TRUE
FROM (
    SELECT DISTINCT make, model
    FROM vehicle
    WHERE make IS NOT NULL AND make != ''
    AND model IS NOT NULL AND model != ''
) v
JOIN brand b ON b.name = v.make
ORDER BY b.name, v.model;

-- Update vehicles to reference the new models
UPDATE vehicle v
SET vehicle_model_id = vm.id
FROM vehicle_model vm
JOIN brand b ON b.id = vm.brand_id
WHERE v.make = b.name AND v.model = vm.name
AND v.make IS NOT NULL AND v.model IS NOT NULL;

-- Add comment to explain migration
COMMENT ON TABLE brand IS 'Vehicle brands/manufacturers (e.g., Toyota, Mercedes-Benz)';
COMMENT ON TABLE vehicle_model IS 'Vehicle models belonging to brands (e.g., Camry, CLK)';
COMMENT ON COLUMN vehicle.vehicle_model_id IS 'Reference to vehicle_model table - replaces legacy make/model fields';
COMMENT ON COLUMN vehicle.make IS 'DEPRECATED: Legacy field, use vehicle_model.brand.name instead';
COMMENT ON COLUMN vehicle.model IS 'DEPRECATED: Legacy field, use vehicle_model.name instead';
