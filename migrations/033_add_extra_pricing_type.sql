-- Add pricing_type column to extra table
-- Values: 'per_day' (default, existing behavior) or 'per_trip' (flat fee per trip)
CREATE TYPE extrapricingtypeenum AS ENUM ('per_day', 'per_trip');

ALTER TABLE extra
    ADD COLUMN IF NOT EXISTS pricing_type extrapricingtypeenum NOT NULL DEFAULT 'per_day';
