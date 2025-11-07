-- Add deposit column to bookings table
ALTER TABLE booking ADD COLUMN deposit NUMERIC(10, 2) DEFAULT 0;
