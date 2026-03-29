-- Rollback: Remove is_private column from tasks

DROP INDEX IF EXISTS idx_tasks_is_private;
ALTER TABLE tasks DROP COLUMN IF EXISTS is_private;
