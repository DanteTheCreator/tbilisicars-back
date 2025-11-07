-- Rollback migration: Remove admin role hierarchy
-- This migration reverts the admin_role column changes

-- Drop the index
DROP INDEX IF EXISTS idx_admins_role;

-- Remove admin_role column
ALTER TABLE admins 
DROP COLUMN admin_role;

-- Note: is_super_admin column remains unchanged as it was kept for compatibility
