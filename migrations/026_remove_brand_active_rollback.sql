-- Rollback migration: Re-add active column to brand table

ALTER TABLE brand ADD COLUMN active BOOLEAN DEFAULT true;
