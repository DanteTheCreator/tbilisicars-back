-- Migration: Add Cases System
-- Description: Creates tables for case management including cases, comments, attachments, and assignments

-- Create cases table
CREATE TABLE cases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    created_by_id INTEGER NOT NULL REFERENCES admins(id),
    related_booking_id INTEGER REFERENCES booking(id),
    related_user_id INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for cases
CREATE INDEX idx_cases_created_by ON cases(created_by_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_related_booking ON cases(related_booking_id);
CREATE INDEX idx_cases_related_user ON cases(related_user_id);
CREATE INDEX idx_cases_created_at ON cases(created_at);

-- Create case_comments table
CREATE TABLE case_comments (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES admins(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for case_comments
CREATE INDEX idx_case_comments_case ON case_comments(case_id);
CREATE INDEX idx_case_comments_admin ON case_comments(admin_id);
CREATE INDEX idx_case_comments_created_at ON case_comments(created_at);

-- Create case_attachments table
CREATE TABLE case_attachments (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES case_comments(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES admins(id),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for case_attachments
CREATE INDEX idx_case_attachments_case ON case_attachments(case_id);
CREATE INDEX idx_case_attachments_comment ON case_attachments(comment_id);
CREATE INDEX idx_case_attachments_admin ON case_attachments(admin_id);

-- Create case_assignments junction table
CREATE TABLE case_assignments (
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, admin_id)
);

-- Create indexes for case_assignments
CREATE INDEX idx_case_assignments_case ON case_assignments(case_id);
CREATE INDEX idx_case_assignments_admin ON case_assignments(admin_id);

-- Add can_manage_cases permission to admins table
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_cases BOOLEAN DEFAULT TRUE;
