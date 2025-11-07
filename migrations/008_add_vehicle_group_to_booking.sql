-- Add vehicle_group_id to booking table
ALTER TABLE booking ADD COLUMN IF NOT EXISTS vehicle_group_id INTEGER REFERENCES vehiclegroup(id) ON DELETE SET NULL;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_booking_vehicle_group_id ON booking(vehicle_group_id);
