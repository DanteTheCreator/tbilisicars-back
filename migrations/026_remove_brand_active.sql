-- Migration: Remove active column from brand table
-- The active field is not needed - brands can simply be deleted if not wanted

ALTER TABLE brand DROP COLUMN IF EXISTS active;
