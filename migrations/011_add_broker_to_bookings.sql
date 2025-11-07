-- Add broker field to bookings table
-- This stores the broker/partner name for bookings from external sources (Discover Cars, VIPCars, etc.)

ALTER TABLE booking ADD COLUMN IF NOT EXISTS broker VARCHAR(100);

-- Add index for faster filtering by broker
CREATE INDEX IF NOT EXISTS idx_booking_broker ON booking(broker);

-- Update existing bookings from email sources
-- (This will be done manually or via application logic based on email source)

COMMENT ON COLUMN booking.broker IS 'Broker/partner name for bookings from external sources (e.g., DiscoverCars, VIPCars)';
