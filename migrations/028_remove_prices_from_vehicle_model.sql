-- Migration 028: Remove price fields from vehicle_model (prices controlled by rates system)

ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price_gel;
ALTER TABLE vehicle_model DROP COLUMN IF EXISTS price_usd;
