-- Rollback: Remove location_type from location table

ALTER TABLE location DROP COLUMN IF EXISTS location_type;

DROP TYPE IF EXISTS location_type_enum;
