-- Migration: Restore payment_status column with simplified enum
-- This fixes the CASCADE deletion issue from migration 017

-- Step 1: Drop the old enum completely
DROP TYPE IF EXISTS paymentstatusenum CASCADE;

-- Step 2: Create new enum with only 4 values
CREATE TYPE paymentstatusenum AS ENUM ('UNPAID', 'HALF', 'PAID', 'REFUNDED');

-- Step 3: Add payment_status column to booking table
ALTER TABLE booking ADD COLUMN payment_status paymentstatusenum NOT NULL DEFAULT 'UNPAID';

-- Step 4: Add status column back to payment table
ALTER TABLE payment ADD COLUMN status paymentstatusenum NOT NULL DEFAULT 'UNPAID';

-- Step 5: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_booking_payment_status ON booking(payment_status);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payment(status);
