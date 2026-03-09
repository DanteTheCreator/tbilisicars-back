-- Migration 031: Add pickup/return photo support for bookings

-- Add direct booking photo references
ALTER TABLE booking ADD COLUMN IF NOT EXISTS pickup_photo VARCHAR(500);
ALTER TABLE booking ADD COLUMN IF NOT EXISTS return_photo VARCHAR(500);

-- Add photo type classification for booking photos
ALTER TABLE bookingphoto ADD COLUMN IF NOT EXISTS photo_type VARCHAR(20) DEFAULT 'GENERAL';
UPDATE bookingphoto SET photo_type = 'GENERAL' WHERE photo_type IS NULL;
ALTER TABLE bookingphoto ALTER COLUMN photo_type SET DEFAULT 'GENERAL';

-- Ensure only allowed values can be stored
ALTER TABLE bookingphoto DROP CONSTRAINT IF EXISTS chk_bookingphoto_photo_type;
ALTER TABLE bookingphoto
    ADD CONSTRAINT chk_bookingphoto_photo_type
    CHECK (photo_type IN ('GENERAL', 'PICKUP', 'RETURN'));

CREATE INDEX IF NOT EXISTS idx_bookingphoto_photo_type ON bookingphoto(photo_type);
COMMENT ON COLUMN booking.pickup_photo IS 'Object name of latest pickup photo for this booking';
COMMENT ON COLUMN booking.return_photo IS 'Object name of latest return photo for this booking';
COMMENT ON COLUMN bookingphoto.photo_type IS 'Photo category: GENERAL, PICKUP, RETURN';
