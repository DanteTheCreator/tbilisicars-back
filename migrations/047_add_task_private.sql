-- Migration: Add is_private column to tasks
-- Private tasks are only visible to the creator and assignees

ALTER TABLE tasks ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX idx_tasks_is_private ON tasks(is_private);
