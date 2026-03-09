-- Rollback: Remove user_id column from damage_report table
DROP INDEX IF EXISTS idx_damage_report_user_id;
ALTER TABLE damage_report DROP COLUMN IF EXISTS user_id;
