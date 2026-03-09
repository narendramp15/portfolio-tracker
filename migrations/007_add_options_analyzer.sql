-- Migration 007: Add Options Analyzer fields to users + new options_analysis_logs table
-- Run with: psql $DATABASE_URL -f migrations/007_add_options_analyzer.sql

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS options_tier VARCHAR(20) NOT NULL DEFAULT 'starter',
    ADD COLUMN IF NOT EXISTS options_credits INTEGER NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS options_analyses_today INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS options_analyses_date VARCHAR(10),
    ADD COLUMN IF NOT EXISTS options_ai_cost_month NUMERIC(10, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS options_ai_cost_month_key VARCHAR(7);

CREATE TABLE IF NOT EXISTS options_analysis_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL,
    analysis_type VARCHAR(20) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    ai_cost_inr NUMERIC(10, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_options_logs_user_id ON options_analysis_logs (user_id);
