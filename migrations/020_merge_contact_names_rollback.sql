-- Rollback Migration 020: Restore contact first name and last name columns

-- Add back the original columns
ALTER TABLE booking ADD COLUMN contact_first_name VARCHAR(100);
ALTER TABLE booking ADD COLUMN contact_last_name VARCHAR(100);

-- Split full_name back (take first word as first name, rest as last name)
UPDATE booking 
SET contact_first_name = SPLIT_PART(contact_full_name, ' ', 1),
    contact_last_name = SUBSTRING(contact_full_name FROM LENGTH(SPLIT_PART(contact_full_name, ' ', 1)) + 2)
WHERE contact_full_name IS NOT NULL;

-- Make them NOT NULL
ALTER TABLE booking ALTER COLUMN contact_first_name SET NOT NULL;
ALTER TABLE booking ALTER COLUMN contact_last_name SET NOT NULL;

-- Drop full_name column
ALTER TABLE booking DROP COLUMN contact_full_name;
