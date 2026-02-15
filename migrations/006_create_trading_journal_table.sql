-- Migration: Create trading_journal table 
-- Date: 2026-02-06  
-- Description: Creates trading_journal table for recording and analyzing trades  
  
-- Create trading_journal table  
CREATE TABLE trading_journal ( 
    id SERIAL PRIMARY KEY,  
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,  
    trade_id INTEGER NOT NULL,  
    symbol VARCHAR(20) NOT NULL,  
    entry_price NUMERIC(20, 8) NOT NULL,  
    exit_price NUMERIC(20, 8),  
    quantity NUMERIC(20, 8) NOT NULL, 
    entry_date TIMESTAMP WITH TIME ZONE NOT NULL,  
    exit_date TIMESTAMP WITH TIME ZONE,  
    profit_loss NUMERIC(20, 2),  
    notes TEXT,  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,  
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,  
  
    CONSTRAINT uix_portfolio_trade UNIQUE (portfolio_id, trade_id)
);  

CREATE INDEX ix_trading_journal_symbol ON trading_journal(symbol);  
CREATE INDEX ix_trading_journal_entry_date ON trading_journal(entry_date);  
CREATE INDEX ix_trading_journal_exit_date ON trading_journal(exit_date);  
CREATE INDEX ix_trading_journal_portfolio_id ON trading_journal(portfolio_id); 
  
COMMENT ON TABLE trading_journal IS 'Table for recording and analyzing trades in the trading journal feature';  
COMMENT ON COLUMN trading_journal.trade_id IS 'Unique trade identifier within the portfolio';  
COMMENT ON COLUMN trading_journal.symbol IS 'Stock symbol (e.g., RELIANCE.NS)';  
COMMENT ON COLUMN trading_journal.entry_price IS 'Price at which the trade was entered';  
COMMENT ON COLUMN trading_journal.exit_price IS 'Price at which the trade was exited';  
COMMENT ON COLUMN trading_journal.quantity IS 'Number of shares traded';  
COMMENT ON COLUMN trading_journal.entry_date IS 'Date and time when the trade was entered'; 
COMMENT ON COLUMN trading_journal.exit_date IS 'Date and time when the trade was exited';  
COMMENT ON COLUMN trading_journal.profit_loss IS 'Profit or loss from the trade (in currency)';  
COMMENT ON COLUMN trading_journal.notes IS 'Additional notes about the trade';  
COMMENT ON COLUMN trading_journal.created_at IS 'Timestamp when the record was created';  
COMMENT ON COLUMN trading_journal.updated_at IS 'Timestamp when the record was last updated';  
  
CREATE OR REPLACE FUNCTION update_updated_at_column()  
RETURNS TRIGGER AS $$  
BEGIN  
    NEW.updated_at = CURRENT_TIMESTAMP;  
    RETURN NEW;  
END;  
$$ language plpgsql;  
  
CREATE TRIGGER update_trading_journal_updated_at  
    BEFORE UPDATE ON trading_journal  
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 
