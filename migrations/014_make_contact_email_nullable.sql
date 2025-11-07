-- Make contact_email nullable in booking table
-- This allows admins to create bookings without requiring an email address

ALTER TABLE booking 
ALTER COLUMN contact_email DROP NOT NULL;
