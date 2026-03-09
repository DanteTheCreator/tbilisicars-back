-- Create booking vehicle assignments table to track vehicle changes with date ranges
CREATE TABLE IF NOT EXISTS booking_vehicle_assignments (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    vehicle_id INTEGER NOT NULL REFERENCES vehicle(id) ON DELETE RESTRICT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    return_location_id INTEGER REFERENCES location(id) ON DELETE SET NULL,
    odometer_reading INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure dates are valid
    CONSTRAINT valid_date_range CHECK (end_date > start_date)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_booking_vehicle_assignments_booking_id ON booking_vehicle_assignments(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_vehicle_assignments_vehicle_id ON booking_vehicle_assignments(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_booking_vehicle_assignments_dates ON booking_vehicle_assignments(start_date, end_date);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_booking_vehicle_assignments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_booking_vehicle_assignments_updated_at
    BEFORE UPDATE ON booking_vehicle_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_booking_vehicle_assignments_updated_at();
