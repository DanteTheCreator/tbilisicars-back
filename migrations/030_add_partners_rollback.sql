-- Rollback script for partners

-- Remove partner_id from booking
DROP INDEX IF EXISTS idx_booking_partner_id;
ALTER TABLE booking DROP COLUMN IF EXISTS partner_id;

-- Drop junction table
DROP INDEX IF EXISTS idx_partner_vehicle_vehicle;
DROP INDEX IF EXISTS idx_partner_vehicle_partner;
DROP TABLE IF EXISTS partner_vehicle;

-- Drop partner documents
DROP INDEX IF EXISTS idx_partner_document_partner_id;
DROP TABLE IF EXISTS partner_document;

-- Drop partner table
DROP INDEX IF EXISTS idx_partner_email;
DROP INDEX IF EXISTS idx_partner_name;
ALTER TABLE partner DROP CONSTRAINT IF EXISTS uq_partner_name;
DROP TABLE IF EXISTS partner;
