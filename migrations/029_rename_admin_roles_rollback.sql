-- Rollback Migration: Rename Admin Roles
-- Reverts admin role values to original naming scheme:
--   admin -> super_admin
--   service_manager -> admin
--   rental_agent -> guest_admin
--   regional_manager -> admin (downgrade to old admin role)

BEGIN;

-- Update admin roles back to original naming scheme
UPDATE admins 
SET admin_role = 'super_admin' 
WHERE admin_role = 'admin';

UPDATE admins 
SET admin_role = 'admin' 
WHERE admin_role IN ('service_manager', 'regional_manager');

UPDATE admins 
SET admin_role = 'guest_admin' 
WHERE admin_role = 'rental_agent';

-- Restore default value for admin_role column
ALTER TABLE admins 
ALTER COLUMN admin_role SET DEFAULT 'guest_admin';

-- Update is_super_admin to match reverted roles
UPDATE admins 
SET is_super_admin = true 
WHERE admin_role = 'super_admin';

UPDATE admins 
SET is_super_admin = false 
WHERE admin_role != 'super_admin';

COMMIT;
