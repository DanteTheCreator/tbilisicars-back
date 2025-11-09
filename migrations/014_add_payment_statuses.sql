-- Add HALF and PREPAID to payment status enum
ALTER TYPE paymentstatusenum ADD VALUE IF NOT EXISTS 'HALF';
ALTER TYPE paymentstatusenum ADD VALUE IF NOT EXISTS 'PREPAID';
