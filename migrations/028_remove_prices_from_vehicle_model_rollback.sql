-- Rollback Migration 028: Restore price fields to vehicle_model

ALTER TABLE vehicle_model ADD COLUMN price NUMERIC(10, 2);
ALTER TABLE vehicle_model ADD COLUMN price_gel NUMERIC(10, 2);
ALTER TABLE vehicle_model ADD COLUMN price_usd NUMERIC(10, 2);

COMMENT ON COLUMN vehicle_model.price IS 'Default/base price for the vehicle model';
COMMENT ON COLUMN vehicle_model.price_gel IS 'Price in Georgian Lari (GEL)';
COMMENT ON COLUMN vehicle_model.price_usd IS 'Price in US Dollars (USD)';
