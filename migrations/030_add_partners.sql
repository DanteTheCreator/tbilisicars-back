-- Create partners table
CREATE TABLE IF NOT EXISTS partner (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    contact_number VARCHAR(50),
    contact_email VARCHAR(150),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add unique constraint on name
ALTER TABLE partner ADD CONSTRAINT uq_partner_name UNIQUE (name);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_partner_name ON partner(name);
CREATE INDEX IF NOT EXISTS idx_partner_email ON partner(contact_email);

-- Create partner_documents table for document uploads
CREATE TABLE IF NOT EXISTS partner_document (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER NOT NULL REFERENCES partner(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add index for partner documents
CREATE INDEX IF NOT EXISTS idx_partner_document_partner_id ON partner_document(partner_id);

-- Create partner_vehicles junction table for many-to-many relationship
CREATE TABLE IF NOT EXISTS partner_vehicle (
    partner_id INTEGER NOT NULL REFERENCES partner(id) ON DELETE CASCADE,
    vehicle_id INTEGER NOT NULL REFERENCES vehicle(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (partner_id, vehicle_id)
);

-- Add indexes for partner_vehicle junction table
CREATE INDEX IF NOT EXISTS idx_partner_vehicle_partner ON partner_vehicle(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_vehicle_vehicle ON partner_vehicle(vehicle_id);

-- Add partner_id to booking table (optional: for tracking which partner a booking came from)
ALTER TABLE booking ADD COLUMN IF NOT EXISTS partner_id INTEGER REFERENCES partner(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_booking_partner_id ON booking(partner_id);

COMMENT ON TABLE partner IS 'Partners/brokers that work with the car rental business';
COMMENT ON TABLE partner_document IS 'Documents uploaded for partners (contracts, agreements, etc.)';
COMMENT ON TABLE partner_vehicle IS 'Junction table linking partners to their associated vehicles';
COMMENT ON COLUMN booking.partner_id IS 'Reference to partner if booking came through a partner';
