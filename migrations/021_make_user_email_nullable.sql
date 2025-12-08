-- Make email nullable in user table to allow bookings without email
-- This allows guest users to be created with only phone number or name

-- Drop the existing unique constraint
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS uq_user_email;

-- Make email column nullable
ALTER TABLE "user" 
ALTER COLUMN email DROP NOT NULL;

-- Create a partial unique index that only enforces uniqueness for non-null emails
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_email ON "user" (email) WHERE email IS NOT NULL;
