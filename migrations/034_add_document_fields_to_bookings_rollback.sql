-- Rollback migration 034: Remove document_type and document_number from bookings
ALTER TABLE booking DROP COLUMN IF EXISTS document_type;
ALTER TABLE booking DROP COLUMN IF EXISTS document_number;
