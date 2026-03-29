-- Migration 043: Add task_assignees junction table for multi-assignee support
CREATE TABLE task_assignees (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, admin_id)
);

-- Migrate existing single-assignee data
INSERT INTO task_assignees (task_id, admin_id)
SELECT id, assigned_to_id FROM tasks WHERE assigned_to_id IS NOT NULL;
