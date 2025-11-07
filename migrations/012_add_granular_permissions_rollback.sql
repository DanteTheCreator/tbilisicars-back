-- Rollback migration 012: Remove granular admin permissions

ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_rates;
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_extras;
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_promotions;
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_locations;
ALTER TABLE admins DROP COLUMN IF EXISTS can_view_reviews;
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_damages;
ALTER TABLE admins DROP COLUMN IF EXISTS can_manage_tasks;
ALTER TABLE admins DROP COLUMN IF EXISTS can_view_calendar;
