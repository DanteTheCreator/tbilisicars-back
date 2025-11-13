-- Migration 020: Merge contact first name and last name into full name

-- Add new full_name column
ALTER TABLE booking ADD COLUMN contact_full_name VARCHAR(200);

-- Migrate existing data
UPDATE booking 
SET contact_full_name = CONCAT(contact_first_name, ' ', contact_last_name)
WHERE contact_first_name IS NOT NULL OR contact_last_name IS NOT NULL;

-- Drop old columns
ALTER TABLE booking DROP COLUMN contact_first_name;
ALTER TABLE booking DROP COLUMN contact_last_name;

-- Make full_name NOT NULL
ALTER TABLE booking ALTER COLUMN contact_full_name SET NOT NULL;
