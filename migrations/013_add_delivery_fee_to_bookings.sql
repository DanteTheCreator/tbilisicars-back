-- Add delivery_fee column to bookings table
-- This fee is charged when vehicle's current location differs from pickup location
ALTER TABLE booking ADD COLUMN delivery_fee NUMERIC(10, 2) DEFAULT 0 NOT NULL;
