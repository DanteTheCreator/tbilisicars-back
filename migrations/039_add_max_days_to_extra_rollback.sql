-- Rollback: remove max_days column from extra table
ALTER TABLE extra DROP COLUMN max_days;
