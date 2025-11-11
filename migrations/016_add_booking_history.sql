-- Add booking_history table to track all changes to bookings
CREATE TABLE IF NOT EXISTS booking_history (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES booking(id) ON DELETE CASCADE,
    changed_by_id INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_booking_history_booking_id ON booking_history(booking_id);
CREATE INDEX idx_booking_history_changed_at ON booking_history(changed_at DESC);
CREATE INDEX idx_booking_history_action_type ON booking_history(action_type);
