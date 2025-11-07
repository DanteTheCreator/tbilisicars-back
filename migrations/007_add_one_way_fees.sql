-- Add one_way_fees table
CREATE TABLE IF NOT EXISTS one_way_fees (
    id SERIAL PRIMARY KEY,
    from_city VARCHAR(100) NOT NULL,
    to_city VARCHAR(100) NOT NULL,
    fee_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_city, to_city)
);

-- Add index for faster lookups
CREATE INDEX idx_one_way_fees_cities ON one_way_fees(from_city, to_city);

-- Insert default one-way fees
INSERT INTO one_way_fees (from_city, to_city, fee_amount, currency) VALUES
    ('Tbilisi', 'Batumi', 60.00, 'EUR'),
    ('Batumi', 'Tbilisi', 60.00, 'EUR'),
    ('Tbilisi', 'Kutaisi', 45.00, 'EUR'),
    ('Kutaisi', 'Tbilisi', 45.00, 'EUR'),
    ('Kutaisi', 'Batumi', 35.00, 'EUR'),
    ('Batumi', 'Kutaisi', 35.00, 'EUR');

-- Add one_way_fee field to bookings table
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS one_way_fee DECIMAL(10, 2) DEFAULT 0.00;

-- Add comment
COMMENT ON TABLE one_way_fees IS 'One-way rental fees when pickup and dropoff cities differ';
COMMENT ON COLUMN bookings.one_way_fee IS 'One-way fee applied to this booking';
