-- Migration: Add broker_id to bookings table
-- This stores the external booking ID from the broker (e.g., Discover Cars booking reference)

ALTER TABLE booking ADD COLUMN IF NOT EXISTS broker_id VARCHAR(100);

-- Create index for faster lookups by broker_id
CREATE INDEX IF NOT EXISTS ix_booking_broker_id ON booking(broker_id);
