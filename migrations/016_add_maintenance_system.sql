-- Create maintenance service types table
CREATE TABLE IF NOT EXISTS maintenance_service_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    average_time_hours NUMERIC(5, 2),
    default_price NUMERIC(10, 2),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create maintenance services table
CREATE TABLE IF NOT EXISTS maintenance_services (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicle(id) ON DELETE CASCADE,
    service_type_id INTEGER NOT NULL REFERENCES maintenance_service_types(id) ON DELETE RESTRICT,
    service_date DATE NOT NULL,
    mileage INTEGER,
    cost NUMERIC(10, 2),
    description TEXT,
    mechanic_name VARCHAR(100),
    shop_name VARCHAR(200),
    next_service_date DATE,
    next_service_mileage INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_maintenance_services_vehicle_id ON maintenance_services(vehicle_id);
CREATE INDEX idx_maintenance_services_service_type_id ON maintenance_services(service_type_id);
CREATE INDEX idx_maintenance_services_service_date ON maintenance_services(service_date);
CREATE INDEX idx_maintenance_services_next_service_date ON maintenance_services(next_service_date);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_maintenance_service_types_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_maintenance_service_types_updated_at
    BEFORE UPDATE ON maintenance_service_types
    FOR EACH ROW
    EXECUTE FUNCTION update_maintenance_service_types_updated_at();

CREATE OR REPLACE FUNCTION update_maintenance_services_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_maintenance_services_updated_at
    BEFORE UPDATE ON maintenance_services
    FOR EACH ROW
    EXECUTE FUNCTION update_maintenance_services_updated_at();

-- Insert some default service types
INSERT INTO maintenance_service_types (name, description, average_time_hours, default_price, active) VALUES
('Oil Change', 'Engine oil and filter replacement', 2, 130, TRUE),
('Braking Pads', 'Brake pad replacement', 2, 70, TRUE),
('Tire Change', 'Tire replacement or rotation', 0, 0, TRUE),
('Technical Check', 'Regular technical inspection', 2, 0, TRUE),
('Visual Damage', 'Visual damage inspection and documentation', 0, 0, TRUE),
('Police Report/Insurance', 'Police report and insurance claim processing', 2, 0, TRUE);
