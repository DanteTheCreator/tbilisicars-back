-- Migration: Add vehicle history tracking
-- Creates vehicle_history table to track all changes made to vehicles

CREATE TABLE vehicle_history (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicle(id) ON DELETE CASCADE,
    changed_by_id INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehicle_history_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicle(id) ON DELETE CASCADE,
    CONSTRAINT fk_vehicle_history_admin FOREIGN KEY (changed_by_id) REFERENCES admins(id) ON DELETE SET NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_vehicle_history_vehicle_id ON vehicle_history(vehicle_id);
CREATE INDEX idx_vehicle_history_changed_at ON vehicle_history(changed_at);
CREATE INDEX idx_vehicle_history_action_type ON vehicle_history(action_type);

COMMENT ON TABLE vehicle_history IS 'Audit trail for all vehicle changes';
COMMENT ON COLUMN vehicle_history.action_type IS 'Type of action: CREATED, STATUS_CHANGED, LOCATION_CHANGED, MILEAGE_UPDATED, MAINTENANCE, etc.';
COMMENT ON COLUMN vehicle_history.field_name IS 'Name of the field that was changed';
COMMENT ON COLUMN vehicle_history.old_value IS 'Previous value of the field';
COMMENT ON COLUMN vehicle_history.new_value IS 'New value of the field';
COMMENT ON COLUMN vehicle_history.description IS 'Human-readable description of the change';
