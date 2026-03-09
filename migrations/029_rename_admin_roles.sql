-- Migration: Rename Admin Roles
-- Updates admin role values to new naming scheme:
--   super_admin -> admin (highest level)
--   admin -> service_manager
--   guest_admin -> rental_agent (lowest level)
-- Adds new regional_manager role between admin and service_manager

BEGIN;

-- Update existing admin roles to new naming scheme
UPDATE admins 
SET admin_role = 'admin' 
WHERE admin_role = 'super_admin';

UPDATE admins 
SET admin_role = 'service_manager' 
WHERE admin_role = 'admin';

UPDATE admins 
SET admin_role = 'rental_agent' 
WHERE admin_role = 'guest_admin';

-- Update default value for admin_role column
ALTER TABLE admins 
ALTER COLUMN admin_role SET DEFAULT 'rental_agent';

-- Update is_super_admin to match new admin role
UPDATE admins 
SET is_super_admin = true 
WHERE admin_role = 'admin';

UPDATE admins 
SET is_super_admin = false 
WHERE admin_role != 'admin';

COMMIT;

-- Note: New role 'regional_manager' is now available but no existing users are assigned to it
-- Super admins can assign this role through the admin panel
