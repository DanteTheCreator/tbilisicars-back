-- Migration: Add rates system for advanced pricing
-- Creates rate, rate_tier, rate_day_range, rate_hour_range, rate_km_range tables

-- Create rate table (main rate strategy)
CREATE TABLE IF NOT EXISTS rate (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_rate_id INTEGER REFERENCES rate(id) ON DELETE SET NULL,
    increment_type VARCHAR(20),
    increment_value NUMERIC(10, 2),
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    min_days INTEGER DEFAULT 2,
    max_days INTEGER DEFAULT 300,
    unlimited_km BOOLEAN DEFAULT TRUE,
    editable_by VARCHAR(50) DEFAULT 'all',
    is_active BOOLEAN DEFAULT TRUE,
    price_modifier_name VARCHAR(100),
    price_modifier_type VARCHAR(20),
    price_modifier_value NUMERIC(10, 2),
    price_modifier_applies_to_agreement_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create rate_tier table (pricing for vehicle group within day ranges)
CREATE TABLE IF NOT EXISTS ratetier (
    id SERIAL PRIMARY KEY,
    rate_id INTEGER NOT NULL REFERENCES rate(id) ON DELETE CASCADE,
    vehicle_group_id INTEGER NOT NULL REFERENCES vehiclegroup(id) ON DELETE CASCADE,
    from_days INTEGER DEFAULT 0,
    to_days INTEGER,
    price_per_day NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create rate_day_range table (day range buckets for rate)
CREATE TABLE IF NOT EXISTS ratedayrange (
    id SERIAL PRIMARY KEY,
    rate_id INTEGER NOT NULL REFERENCES rate(id) ON DELETE CASCADE,
    from_days INTEGER NOT NULL,
    to_days INTEGER,
    label VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create rate_hour_range table (hourly pricing ranges)
CREATE TABLE IF NOT EXISTS ratehourrange (
    id SERIAL PRIMARY KEY,
    rate_id INTEGER NOT NULL REFERENCES rate(id) ON DELETE CASCADE,
    from_hours INTEGER NOT NULL,
    to_hours INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create rate_km_range table (km/mileage ranges)
CREATE TABLE IF NOT EXISTS ratekmrange (
    id SERIAL PRIMARY KEY,
    rate_id INTEGER NOT NULL REFERENCES rate(id) ON DELETE CASCADE,
    from_km INTEGER DEFAULT 0,
    to_km INTEGER,
    label VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_rate_name ON rate(name);
CREATE INDEX IF NOT EXISTS idx_rate_active ON rate(is_active);
CREATE INDEX IF NOT EXISTS idx_rate_valid_from ON rate(valid_from);
CREATE INDEX IF NOT EXISTS idx_rate_parent_rate ON rate(parent_rate_id);

CREATE INDEX IF NOT EXISTS idx_ratetier_rate ON ratetier(rate_id);
CREATE INDEX IF NOT EXISTS idx_ratetier_vehicle_group ON ratetier(vehicle_group_id);

CREATE INDEX IF NOT EXISTS idx_ratedayrange_rate ON ratedayrange(rate_id);
CREATE INDEX IF NOT EXISTS idx_ratehourrange_rate ON ratehourrange(rate_id);
CREATE INDEX IF NOT EXISTS idx_ratekmrange_rate ON ratekmrange(rate_id);

-- Add triggers to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_rate_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_rate_updated_at
    BEFORE UPDATE ON rate
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_updated_at();

CREATE TRIGGER trigger_update_ratetier_updated_at
    BEFORE UPDATE ON ratetier
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_updated_at();

CREATE TRIGGER trigger_update_ratedayrange_updated_at
    BEFORE UPDATE ON ratedayrange
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_updated_at();

CREATE TRIGGER trigger_update_ratehourrange_updated_at
    BEFORE UPDATE ON ratehourrange
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_updated_at();

CREATE TRIGGER trigger_update_ratekmrange_updated_at
    BEFORE UPDATE ON ratekmrange
    FOR EACH ROW
    EXECUTE FUNCTION update_rate_updated_at();

-- Insert sample data matching the screenshot
-- Main rate: TBILISICARS-MAIN
INSERT INTO rate (name, description, valid_from, valid_until, min_days, max_days, unlimited_km, editable_by, is_active)
VALUES 
    ('TBILISICARS-MAIN', 'Main pricing rate for all vehicle groups', '2025-10-20', '2025-12-20', 2, 300, TRUE, 'all', TRUE);

-- Sample day ranges (0-3, 4-7, 8-13, 14-30, 31-364)
INSERT INTO ratedayrange (rate_id, from_days, to_days, label)
SELECT id, 0, 3, 'From 0 to 3 Days' FROM rate WHERE name = 'TBILISICARS-MAIN'
UNION ALL
SELECT id, 4, 7, 'From 4 to 7 Days' FROM rate WHERE name = 'TBILISICARS-MAIN'
UNION ALL
SELECT id, 8, 13, 'From 8 to 13 Days' FROM rate WHERE name = 'TBILISICARS-MAIN'
UNION ALL
SELECT id, 14, 30, 'From 14 to 30 Days' FROM rate WHERE name = 'TBILISICARS-MAIN'
UNION ALL
SELECT id, 31, 364, 'From 31 to 364 Days' FROM rate WHERE name = 'TBILISICARS-MAIN';

-- Note: Rate tiers (pricing matrix) should be added via API
-- as they depend on the vehicle groups that exist in your system
