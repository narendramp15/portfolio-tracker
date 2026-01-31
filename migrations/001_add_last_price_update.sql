"""
Add last_price_update column to assets table.

Run this SQL in your PostgreSQL database (Neon console or any SQL client):
"""

-- Add last_price_update column to assets table
ALTER TABLE assets 
ADD COLUMN last_price_update TIMESTAMP WITH TIME ZONE;

-- Set default value for existing rows (current timestamp)
UPDATE assets 
SET last_price_update = CURRENT_TIMESTAMP 
WHERE last_price_update IS NULL;

-- Add comment
COMMENT ON COLUMN assets.last_price_update IS 'Timestamp of last price update from market data';
