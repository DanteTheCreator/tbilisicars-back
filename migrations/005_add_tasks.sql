-- Migration: Add tasks table
-- This migration creates the tasks table for admin task management

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Dates
    deadline TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Status and Priority
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    
    -- Foreign Keys
    created_by_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    assigned_to_id INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    
    -- Related entities (optional)
    related_vehicle_id INTEGER REFERENCES vehicle(id) ON DELETE SET NULL,
    related_booking_id INTEGER REFERENCES booking(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for performance
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_created_by ON tasks(created_by_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_tasks_related_vehicle ON tasks(related_vehicle_id);
CREATE INDEX idx_tasks_related_booking ON tasks(related_booking_id);
