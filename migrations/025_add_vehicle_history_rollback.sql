-- Rollback migration: Remove vehicle history tracking

DROP TABLE IF EXISTS vehicle_history CASCADE;
