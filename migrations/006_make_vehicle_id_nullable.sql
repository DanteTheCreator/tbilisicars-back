-- Make vehicle_id nullable and change foreign key to SET NULL on delete
ALTER TABLE booking DROP CONSTRAINT IF EXISTS booking_vehicle_id_fkey;
ALTER TABLE booking ALTER COLUMN vehicle_id DROP NOT NULL;
ALTER TABLE booking ADD CONSTRAINT booking_vehicle_id_fkey 
    FOREIGN KEY (vehicle_id) REFERENCES vehicle(id) ON DELETE SET NULL;
