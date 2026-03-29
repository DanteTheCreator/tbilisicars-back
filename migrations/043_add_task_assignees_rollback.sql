-- Migration 043 rollback: Remove task_assignees junction table
DROP TABLE IF EXISTS task_assignees;
