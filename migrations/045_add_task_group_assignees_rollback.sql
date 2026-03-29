-- Migration 045 rollback: Remove task_group_assignees junction table
DROP INDEX IF EXISTS idx_task_group_assignees_group;
DROP INDEX IF EXISTS idx_task_group_assignees_task;
DROP TABLE IF EXISTS task_group_assignees;
