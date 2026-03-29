-- Rollback migration 044: Remove admin groups system
DROP TABLE IF EXISTS admin_group_members;
DROP TABLE IF EXISTS admin_groups;
