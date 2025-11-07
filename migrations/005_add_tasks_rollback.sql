-- Rollback migration: Remove tasks table

DROP INDEX IF EXISTS idx_tasks_related_booking;
DROP INDEX IF EXISTS idx_tasks_related_vehicle;
DROP INDEX IF EXISTS idx_tasks_deadline;
DROP INDEX IF EXISTS idx_tasks_assigned_to;
DROP INDEX IF EXISTS idx_tasks_created_by;
DROP INDEX IF EXISTS idx_tasks_priority;
DROP INDEX IF EXISTS idx_tasks_status;

DROP TABLE IF EXISTS tasks;
