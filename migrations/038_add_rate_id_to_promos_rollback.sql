-- Rollback: remove rate_id column from promo table
DROP INDEX IF EXISTS ix_promo_rate_id;
ALTER TABLE promo DROP COLUMN IF EXISTS rate_id;
