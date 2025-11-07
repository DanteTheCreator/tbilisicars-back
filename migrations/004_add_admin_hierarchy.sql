-- Migration: Add admin role hierarchy
-- This migration adds the admin_role column to the admins table
-- and migrates existing is_super_admin data to the new role system

-- Add admin_role column with default value
ALTER TABLE admins 
ADD COLUMN admin_role VARCHAR(20) NOT NULL DEFAULT 'guest_admin';

-- Migrate existing data: convert is_super_admin to admin_role
UPDATE admins 
SET admin_role = CASE 
    WHEN is_super_admin = true THEN 'super_admin'
    ELSE 'admin'
END;

-- Note: is_super_admin column is kept for backward compatibility
-- It can be removed in a future migration after ensuring all systems are updated

-- Add index for faster role-based queries
CREATE INDEX idx_admins_role ON admins(admin_role);
