-- Simplify payment status enum to only 4 essential values
-- Keep: UNPAID, HALF, PAID, REFUNDED

-- First, ensure all existing data uses compatible values (already UNPAID or PAID)
-- No data migration needed since current data only has UNPAID and PAID

-- Recreate the enum with only the 4 core values
ALTER TYPE paymentstatusenum RENAME TO paymentstatusenum_old;

CREATE TYPE paymentstatusenum AS ENUM ('UNPAID', 'HALF', 'PAID', 'REFUNDED');

-- Update booking table
ALTER TABLE booking 
    ALTER COLUMN payment_status TYPE paymentstatusenum USING payment_status::text::paymentstatusenum,
    ALTER COLUMN payment_status SET DEFAULT 'UNPAID';

-- Update payment table  
ALTER TABLE payment 
    ALTER COLUMN status TYPE paymentstatusenum USING status::text::paymentstatusenum;

DROP TYPE paymentstatusenum_old;
