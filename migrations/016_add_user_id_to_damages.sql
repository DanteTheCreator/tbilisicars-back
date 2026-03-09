-- Add user_id column to damage_report table
ALTER TABLE damage_report 
ADD COLUMN user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL;

CREATE INDEX idx_damage_report_user_id ON damage_report(user_id);
