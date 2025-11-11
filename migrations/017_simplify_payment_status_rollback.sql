-- Rollback: Restore original payment status enum with all values
ALTER TYPE paymentstatusenum RENAME TO paymentstatusenum_new;

CREATE TYPE paymentstatusenum AS ENUM ('UNPAID', 'AUTHORIZED', 'PARTIAL', 'HALF', 'PREPAID', 'PAID', 'REFUNDED');

ALTER TABLE booking 
    ALTER COLUMN payment_status TYPE paymentstatusenum USING payment_status::text::paymentstatusenum;

DROP TYPE paymentstatusenum_new;

-- Note: Data migration (PENDING->UNPAID, etc.) would need to be handled manually if rolling back
