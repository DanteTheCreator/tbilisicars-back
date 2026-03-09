-- Drop triggers
DROP TRIGGER IF EXISTS trigger_update_maintenance_services_updated_at ON maintenance_services;
DROP TRIGGER IF EXISTS trigger_update_maintenance_service_types_updated_at ON maintenance_service_types;

-- Drop functions
DROP FUNCTION IF EXISTS update_maintenance_services_updated_at();
DROP FUNCTION IF EXISTS update_maintenance_service_types_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_maintenance_services_next_service_date;
DROP INDEX IF EXISTS idx_maintenance_services_service_date;
DROP INDEX IF EXISTS idx_maintenance_services_service_type_id;
DROP INDEX IF EXISTS idx_maintenance_services_vehicle_id;

-- Drop tables (in reverse order due to foreign keys)
DROP TABLE IF EXISTS maintenance_services;
DROP TABLE IF EXISTS maintenance_service_types;
