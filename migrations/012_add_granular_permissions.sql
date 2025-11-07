-- Add granular permissions for each admin section
-- Migration 012: Add granular admin permissions

ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_rates BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_extras BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_promotions BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_locations BOOLEAN DEFAULT FALSE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_view_reviews BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_damages BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_manage_tasks BOOLEAN DEFAULT TRUE;
ALTER TABLE admins ADD COLUMN IF NOT EXISTS can_view_calendar BOOLEAN DEFAULT TRUE;

-- Update existing admins to have all permissions enabled by default (except locations which requires settings access)
UPDATE admins SET 
    can_manage_rates = TRUE,
    can_manage_extras = TRUE,
    can_manage_promotions = TRUE,
    can_manage_locations = CASE WHEN can_manage_settings = TRUE THEN TRUE ELSE FALSE END,
    can_view_reviews = TRUE,
    can_manage_damages = TRUE,
    can_manage_tasks = TRUE,
    can_view_calendar = TRUE
WHERE can_manage_rates IS NULL;
