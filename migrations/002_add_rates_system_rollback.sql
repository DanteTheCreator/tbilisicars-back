-- Rollback Migration: Remove rates system

-- Drop triggers
DROP TRIGGER IF EXISTS trigger_update_ratekmrange_updated_at ON ratekmrange;
DROP TRIGGER IF EXISTS trigger_update_ratehourrange_updated_at ON ratehourrange;
DROP TRIGGER IF EXISTS trigger_update_ratedayrange_updated_at ON ratedayrange;
DROP TRIGGER IF EXISTS trigger_update_ratetier_updated_at ON ratetier;
DROP TRIGGER IF EXISTS trigger_update_rate_updated_at ON rate;

-- Drop function
DROP FUNCTION IF EXISTS update_rate_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_ratekmrange_rate;
DROP INDEX IF EXISTS idx_ratehourrange_rate;
DROP INDEX IF EXISTS idx_ratedayrange_rate;
DROP INDEX IF EXISTS idx_ratetier_vehicle_group;
DROP INDEX IF EXISTS idx_ratetier_rate;
DROP INDEX IF EXISTS idx_rate_parent_rate;
DROP INDEX IF EXISTS idx_rate_valid_from;
DROP INDEX IF EXISTS idx_rate_active;
DROP INDEX IF EXISTS idx_rate_name;

-- Drop tables (in reverse order due to foreign keys)
DROP TABLE IF EXISTS ratekmrange;
DROP TABLE IF EXISTS ratehourrange;
DROP TABLE IF EXISTS ratedayrange;
DROP TABLE IF EXISTS ratetier;
DROP TABLE IF EXISTS rate;
