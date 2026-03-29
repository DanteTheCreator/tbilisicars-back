-- Add rate_id column to promo table so promotions can be linked to a specific rate
ALTER TABLE promo ADD COLUMN IF NOT EXISTS rate_id INTEGER REFERENCES rate(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_promo_rate_id ON promo(rate_id);
