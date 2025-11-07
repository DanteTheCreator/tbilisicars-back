-- Add starting_price column to vehicles for display purposes
-- This is a fallback/default price when rates are not available

ALTER TABLE vehicle ADD COLUMN starting_price NUMERIC(10,2) DEFAULT 50.00;

-- Set default prices based on vehicle class
UPDATE vehicle SET starting_price = 35.00 WHERE vehicle_class = 'ECONOMY';
UPDATE vehicle SET starting_price = 45.00 WHERE vehicle_class = 'COMPACT';
UPDATE vehicle SET starting_price = 60.00 WHERE vehicle_class = 'MIDSIZE';
UPDATE vehicle SET starting_price = 75.00 WHERE vehicle_class = 'FULLSIZE';
UPDATE vehicle SET starting_price = 120.00 WHERE vehicle_class = 'LUXURY';
UPDATE vehicle SET starting_price = 85.00 WHERE vehicle_class = 'SUV';
UPDATE vehicle SET starting_price = 95.00 WHERE vehicle_class = 'VAN';
UPDATE vehicle SET starting_price = 110.00 WHERE vehicle_class = 'TRUCK';

-- Add index for better query performance
CREATE INDEX idx_vehicle_starting_price ON vehicle(starting_price);

-- Add comment
COMMENT ON COLUMN vehicle.starting_price IS 'Starting price for display - actual price calculated from rates';
