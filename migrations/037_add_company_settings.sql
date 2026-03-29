-- Create company_settings table (singleton for company info)
CREATE TABLE IF NOT EXISTS company_settings (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL DEFAULT 'TbilisiCars',
    company_legal_name VARCHAR(200) NOT NULL DEFAULT 'TbilisiCars LLC',
    company_email VARCHAR(255) NOT NULL DEFAULT 'reservations@tbilisicars.com',
    company_phone VARCHAR(50) NOT NULL DEFAULT '+995 591 00 26 30',
    company_address VARCHAR(500) NOT NULL DEFAULT 'Tbilisi, Georgia',
    company_website VARCHAR(255) NOT NULL DEFAULT 'https://tbilisicars.live',
    default_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    default_timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Tbilisi',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert the single settings row
INSERT INTO company_settings (id, company_name, company_legal_name, company_email, company_phone, company_address, company_website, default_currency, default_timezone)
VALUES (1, 'TbilisiCars', 'TbilisiCars LLC', 'reservations@tbilisicars.com', '+995 591 00 26 30', 'Tbilisi, Georgia', 'https://tbilisicars.live', 'USD', 'Asia/Tbilisi')
ON CONFLICT DO NOTHING;
