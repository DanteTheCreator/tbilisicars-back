-- Migration 045: Add task_group_assignees junction table for group-based task assignment
CREATE TABLE IF NOT EXISTS task_group_assignees (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES admin_groups(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, group_id)
);

CREATE INDEX idx_task_group_assignees_task ON task_group_assignees(task_id);
CREATE INDEX idx_task_group_assignees_group ON task_group_assignees(group_id);
