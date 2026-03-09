-- Migration 034: Add document_type and document_number to bookings
ALTER TABLE booking ADD COLUMN IF NOT EXISTS document_type VARCHAR(20);
ALTER TABLE booking ADD COLUMN IF NOT EXISTS document_number VARCHAR(100);
