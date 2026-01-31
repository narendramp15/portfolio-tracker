-- Migration: Add previous_close column to assets table
-- This column stores the previous day's closing price for calculating today's change

ALTER TABLE assets ADD COLUMN previous_close NUMERIC(20, 8) NULL;

-- Optional: Add comment explaining the column purpose
COMMENT ON COLUMN assets.previous_close IS 'Previous day closing price for calculating today''s change';
