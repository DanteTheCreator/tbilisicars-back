-- Migration 036: Add vehicle_model_id to booking table
-- Bookings now track which vehicle model was requested instead of vehicle group

ALTER TABLE booking ADD COLUMN IF NOT EXISTS vehicle_model_id INTEGER;

-- Add foreign key constraint
ALTER TABLE booking
    ADD CONSTRAINT fk_booking_vehicle_model
    FOREIGN KEY (vehicle_model_id)
    REFERENCES vehicle_model(id)
    ON DELETE SET NULL;

-- Add index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_booking_vehicle_model_id ON booking(vehicle_model_id);

-- Backfill: For existing bookings that have a vehicle_id, populate vehicle_model_id
UPDATE booking b
SET vehicle_model_id = v.vehicle_model_id
FROM vehicle v
WHERE b.vehicle_id = v.id
  AND v.vehicle_model_id IS NOT NULL
  AND b.vehicle_model_id IS NULL;

-- Also backfill from vehicle_group: if booking has vehicle_group_id but no vehicle_model_id,
-- pick the first vehicle_model that belongs to a vehicle in that group
UPDATE booking b
SET vehicle_model_id = sub.vehicle_model_id
FROM (
    SELECT DISTINCT ON (v.vehicle_group_id) v.vehicle_group_id, v.vehicle_model_id
    FROM vehicle v
    WHERE v.vehicle_model_id IS NOT NULL AND v.vehicle_group_id IS NOT NULL
    ORDER BY v.vehicle_group_id, v.id
) sub
WHERE b.vehicle_group_id = sub.vehicle_group_id
  AND b.vehicle_model_id IS NULL;
