-- Rollback Migration 031: Remove pickup/return photo support for bookings

DROP INDEX IF EXISTS idx_bookingphoto_photo_type;
ALTER TABLE bookingphoto DROP CONSTRAINT IF EXISTS chk_bookingphoto_photo_type;
ALTER TABLE bookingphoto DROP COLUMN IF EXISTS photo_type;

ALTER TABLE booking DROP COLUMN IF EXISTS pickup_photo;
ALTER TABLE booking DROP COLUMN IF EXISTS return_photo;
