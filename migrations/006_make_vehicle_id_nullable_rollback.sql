-- Rollback: Make vehicle_id NOT NULL again
ALTER TABLE booking DROP CONSTRAINT IF EXISTS booking_vehicle_id_fkey;
ALTER TABLE booking ALTER COLUMN vehicle_id SET NOT NULL;
ALTER TABLE booking ADD CONSTRAINT booking_vehicle_id_fkey 
    FOREIGN KEY (vehicle_id) REFERENCES vehicle(id) ON DELETE RESTRICT;
