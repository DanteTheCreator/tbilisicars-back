-- Add source column to booking table to track where the booking came from
ALTER TABLE booking ADD COLUMN IF NOT EXISTS source VARCHAR(20);

-- Create index for filtering by source
CREATE INDEX IF NOT EXISTS ix_booking_source ON booking (source);

-- Backfill existing bookings: web bookings (broker = 'Web')
UPDATE booking SET source = 'web' WHERE broker = 'Web' AND source IS NULL;

-- Backfill existing bookings: broker bookings (has a real broker, not 'Web')
UPDATE booking SET source = 'broker' WHERE broker IS NOT NULL AND broker != 'Web' AND source IS NULL;

-- Backfill existing bookings: web bookings (CREATED history entry with no admin)
UPDATE booking SET source = 'web'
WHERE source IS NULL
  AND id IN (
    SELECT booking_id FROM booking_history
    WHERE action_type = 'CREATED' AND changed_by_id IS NULL
  );

-- Backfill existing bookings: admin bookings (CREATED history entry with admin)
UPDATE booking SET source = 'admin'
WHERE source IS NULL
  AND id IN (
    SELECT booking_id FROM booking_history
    WHERE action_type = 'CREATED' AND changed_by_id IS NOT NULL
  );

-- Any remaining bookings without history default to 'admin'
UPDATE booking SET source = 'admin' WHERE source IS NULL;
