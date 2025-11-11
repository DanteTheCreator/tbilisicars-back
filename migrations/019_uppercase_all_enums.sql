-- Migration: Convert all enum values to uppercase for consistency
-- This aligns database enums with Python models

-- 1. Fix bookingstatusenum - remove lowercase 'delivered' duplicate
ALTER TYPE bookingstatusenum RENAME TO bookingstatusenum_old;

CREATE TYPE bookingstatusenum AS ENUM ('PENDING', 'CONFIRMED', 'DELIVERED', 'RETURNED', 'CANCELED', 'NO_SHOW');

-- Update booking table
ALTER TABLE booking ALTER COLUMN status TYPE bookingstatusenum USING 
    CASE 
        WHEN status::text = 'delivered' THEN 'DELIVERED'::bookingstatusenum
        ELSE status::text::bookingstatusenum
    END;

DROP TYPE bookingstatusenum_old;

-- 2. Fix extratypeenum - convert to uppercase
ALTER TYPE extratypeenum RENAME TO extratypeenum_old;

CREATE TYPE extratypeenum AS ENUM ('GPS', 'CHILD_SEAT', 'EXTRA_DRIVER', 'ROOF_RACK', 'WIFI', 'SNOW_CHAINS');

-- Update extra table
ALTER TABLE extra ALTER COLUMN type TYPE text;
UPDATE extra SET type = 
    CASE 
        WHEN type = 'gps' THEN 'GPS'
        WHEN type = 'child_seat' THEN 'CHILD_SEAT'
        WHEN type = 'extra_driver' THEN 'EXTRA_DRIVER'
        WHEN type = 'roof_rack' THEN 'ROOF_RACK'
        WHEN type = 'wifi' THEN 'WIFI'
        WHEN type = 'snow_chains' THEN 'SNOW_CHAINS'
        ELSE type
    END;
ALTER TABLE extra ALTER COLUMN type TYPE extratypeenum USING type::extratypeenum;

DROP TYPE extratypeenum_old;

-- 3. Fix paymentmethodenum - convert to uppercase
ALTER TYPE paymentmethodenum RENAME TO paymentmethodenum_old;

CREATE TYPE paymentmethodenum AS ENUM ('CARD', 'CASH', 'BANK_TRANSFER', 'STRIPE', 'PAYPAL');

-- Update payment table
ALTER TABLE payment ALTER COLUMN method TYPE text;
UPDATE payment SET method = 
    CASE 
        WHEN method = 'card' THEN 'CARD'
        WHEN method = 'cash' THEN 'CASH'
        WHEN method = 'bank_transfer' THEN 'BANK_TRANSFER'
        WHEN method = 'stripe' THEN 'STRIPE'
        WHEN method = 'paypal' THEN 'PAYPAL'
        ELSE method
    END;
ALTER TABLE payment ALTER COLUMN method TYPE paymentmethodenum USING method::paymentmethodenum;

DROP TYPE paymentmethodenum_old;

-- 4. Fix documenttypeenum - convert to uppercase
ALTER TYPE documenttypeenum RENAME TO documenttypeenum_old;

CREATE TYPE documenttypeenum AS ENUM ('REGISTRATION', 'INSURANCE', 'INSPECTION', 'OTHER');

-- Update vehicledocument table
ALTER TABLE vehicledocument ALTER COLUMN type TYPE text;
UPDATE vehicledocument SET type = 
    CASE 
        WHEN type = 'registration' THEN 'REGISTRATION'
        WHEN type = 'insurance' THEN 'INSURANCE'
        WHEN type = 'inspection' THEN 'INSPECTION'
        WHEN type = 'other' THEN 'OTHER'
        ELSE type
    END;
ALTER TABLE vehicledocument ALTER COLUMN type TYPE documenttypeenum USING type::documenttypeenum;

DROP TYPE documenttypeenum_old;

-- 5. Fix damageseverityenum - convert to uppercase
ALTER TYPE damageseverityenum RENAME TO damageseverityenum_old;

CREATE TYPE damageseverityenum AS ENUM ('MINOR', 'MODERATE', 'MAJOR');

-- Update damagereport table
ALTER TABLE damagereport ALTER COLUMN severity TYPE text;
UPDATE damagereport SET severity = 
    CASE 
        WHEN severity = 'minor' THEN 'MINOR'
        WHEN severity = 'moderate' THEN 'MODERATE'
        WHEN severity = 'major' THEN 'MAJOR'
        ELSE severity
    END;
ALTER TABLE damagereport ALTER COLUMN severity TYPE damageseverityenum USING severity::damageseverityenum;

DROP TYPE damageseverityenum_old;

-- 6. Fix pricetypeenum - convert to uppercase
ALTER TYPE pricetypeenum RENAME TO pricetypeenum_old;

CREATE TYPE pricetypeenum AS ENUM ('BASE_DAILY', 'WEEKLY', 'MONTHLY', 'WEEKEND', 'SEASONAL', 'ONE_WAY_FEE');

-- Update vehicleprice table
ALTER TABLE vehicleprice ALTER COLUMN price_type TYPE text;
UPDATE vehicleprice SET price_type = 
    CASE 
        WHEN price_type = 'base_daily' THEN 'BASE_DAILY'
        WHEN price_type = 'weekly' THEN 'WEEKLY'
        WHEN price_type = 'monthly' THEN 'MONTHLY'
        WHEN price_type = 'weekend' THEN 'WEEKEND'
        WHEN price_type = 'seasonal' THEN 'SEASONAL'
        WHEN price_type = 'one_way_fee' THEN 'ONE_WAY_FEE'
        ELSE price_type
    END;
ALTER TABLE vehicleprice ALTER COLUMN price_type TYPE pricetypeenum USING price_type::pricetypeenum;

DROP TYPE pricetypeenum_old;

-- Note: The following enums are already uppercase and don't need changes:
-- - currencyenum (USD, EUR, GBP, GEL)
-- - discounttypeenum (PERCENT, FIXED)
-- - fueltypeenum (GASOLINE, DIESEL, HYBRID, ELECTRIC)
-- - transmissionenum (MANUAL, AUTOMATIC)
-- - vehicleclassenum (all uppercase)
-- - vehiclestatusenum (all uppercase)
-- - paymentstatusenum (UNPAID, HALF, PAID, REFUNDED)
-- - maintenancetypeenum (all uppercase, but unused in models - can be left as is)
