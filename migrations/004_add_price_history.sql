-- Migration: Add price_history table
-- Efficient storage for historical prices on free-tier deployments

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date TIMESTAMP NOT NULL,
    close NUMERIC(12, 2) NOT NULL
);

-- Create unique constraint to prevent duplicates
ALTER TABLE price_history ADD CONSTRAINT uix_symbol_date UNIQUE (symbol, date);

-- Create composite index for efficient queries
CREATE INDEX IF NOT EXISTS ix_price_history_symbol_date ON price_history (symbol, date);

-- Create index on symbol for filtering
CREATE INDEX IF NOT EXISTS ix_price_history_symbol ON price_history (symbol);
