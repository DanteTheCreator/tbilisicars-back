-- Rollback: Make contact_email required again in booking table

ALTER TABLE booking 
ALTER COLUMN contact_email SET NOT NULL;
