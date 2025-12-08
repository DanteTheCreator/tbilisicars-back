-- Rollback: Make email required again in user table
-- Warning: This will fail if there are users with NULL email

-- Drop the partial unique index
DROP INDEX IF EXISTS uq_user_email;

-- Make email required again
ALTER TABLE "user" 
ALTER COLUMN email SET NOT NULL;

-- Recreate the original unique constraint
ALTER TABLE "user" ADD CONSTRAINT uq_user_email UNIQUE (email);
