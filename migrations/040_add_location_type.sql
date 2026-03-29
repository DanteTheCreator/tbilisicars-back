-- Migration: Add location_type to location table
-- Types: meet_and_greet, rental_office

CREATE TYPE location_type_enum AS ENUM ('meet_and_greet', 'rental_office');

ALTER TABLE location
    ADD COLUMN IF NOT EXISTS location_type location_type_enum NOT NULL DEFAULT 'meet_and_greet';
