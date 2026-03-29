-- Migration 044: Add admin groups system
-- Groups allow admins to be organized and share permissions at the group level

-- Admin groups table
CREATE TABLE IF NOT EXISTS admin_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    -- Group-level permissions (same as admin-level)
    can_manage_vehicles BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_bookings BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_users BOOLEAN NOT NULL DEFAULT FALSE,
    can_view_reports BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_settings BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_rates BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_extras BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_promotions BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_locations BOOLEAN NOT NULL DEFAULT FALSE,
    can_view_reviews BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_damages BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_tasks BOOLEAN NOT NULL DEFAULT FALSE,
    can_view_calendar BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_cases BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Junction table for admin-group many-to-many relationship
CREATE TABLE IF NOT EXISTS admin_group_members (
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES admin_groups(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (admin_id, group_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_admin_group_members_admin ON admin_group_members(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_group_members_group ON admin_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_admin_groups_name ON admin_groups(name);
