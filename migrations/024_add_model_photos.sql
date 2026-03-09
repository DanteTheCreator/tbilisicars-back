-- Migration 024: Update VehiclePhoto to support both vehicles and models
-- Allows photos to be attached to vehicle models and shared across all vehicles of that model

-- Add vehicle_model_id column to vehiclephoto table
ALTER TABLE vehiclephoto ADD COLUMN vehicle_model_id INTEGER REFERENCES vehicle_model(id) ON DELETE CASCADE;
CREATE INDEX idx_vehiclephoto_model_id ON vehiclephoto(vehicle_model_id);

-- Make vehicle_id nullable (photos can now belong to either vehicle OR model)
ALTER TABLE vehiclephoto ALTER COLUMN vehicle_id DROP NOT NULL;

-- Add constraint to ensure photo belongs to either vehicle OR model (not both, not neither)
ALTER TABLE vehiclephoto ADD CONSTRAINT chk_vehiclephoto_owner 
    CHECK (
        (vehicle_id IS NOT NULL AND vehicle_model_id IS NULL) OR
        (vehicle_id IS NULL AND vehicle_model_id IS NOT NULL)
    );

-- Add comment to explain the change
COMMENT ON COLUMN vehiclephoto.vehicle_model_id IS 'Reference to vehicle_model - photos can be shared across all vehicles of this model';
COMMENT ON COLUMN vehiclephoto.vehicle_id IS 'Reference to specific vehicle - takes precedence over model photos';
COMMENT ON TABLE vehiclephoto IS 'Photos for vehicles or models. Model photos are shared by all vehicles of that model unless vehicle has specific photos.';
