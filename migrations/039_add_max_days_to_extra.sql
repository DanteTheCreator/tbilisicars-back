-- Add max_days column to extra table
-- max_days: the maximum number of days charged for a per_day extra (NULL = no limit)
ALTER TABLE extra ADD COLUMN max_days INTEGER NULL;
