-- Add rate tracking columns to bookings table
-- This allows us to track which rate and tier were used for each booking

ALTER TABLE booking ADD COLUMN rate_id INTEGER REFERENCES rate(id) ON DELETE SET NULL;
ALTER TABLE booking ADD COLUMN rate_tier_id INTEGER REFERENCES ratetier(id) ON DELETE SET NULL;
ALTER TABLE booking ADD COLUMN price_per_day NUMERIC(10,2);

-- Add indexes for better query performance
CREATE INDEX idx_booking_rate_id ON booking(rate_id);
CREATE INDEX idx_booking_rate_tier_id ON booking(rate_tier_id);

-- Add comments for documentation
COMMENT ON COLUMN booking.rate_id IS 'The rate used to calculate pricing for this booking';
COMMENT ON COLUMN booking.rate_tier_id IS 'The specific rate tier used (contains the day range and price)';
COMMENT ON COLUMN booking.price_per_day IS 'Price per day at the time of booking (for historical accuracy)';
