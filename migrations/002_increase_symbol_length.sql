-- Migration: Increase symbol column length to support exchange suffixes
-- Date: 2026-01-31
-- Description: Changes assets.symbol from VARCHAR(10) to VARCHAR(20) to support symbols like RELIANCE.NS

-- Increase symbol column length
ALTER TABLE assets ALTER COLUMN symbol TYPE VARCHAR(20);

-- No data migration needed - existing symbols will fit in new length
