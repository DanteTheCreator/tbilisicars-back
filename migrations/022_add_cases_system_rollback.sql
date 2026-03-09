-- Rollback Migration: Remove Cases System
-- Description: Drops all tables and columns related to case management

-- Drop case_assignments table
DROP TABLE IF EXISTS case_assignments;

-- Drop case_attachments table
DROP TABLE IF EXISTS case_attachments;

-- Drop case_comments table
DROP TABLE IF EXISTS case_comments;

-- Drop cases table
DROP TABLE IF EXISTS cases;

-- Remove can_manage_cases permission from admins table
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_cases;
