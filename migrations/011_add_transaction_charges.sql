-- Migration 011: Record transaction charges.
--
-- Transactions previously stored only quantity and price, so every capital
-- gains figure ignored the cost of trading. Under Section 48 brokerage and
-- other transfer expenses are deductible against the gain while STT is not,
-- so the three are stored separately rather than as one lumped "charges"
-- column.
--
-- Existing rows default to 0, which reproduces today's behaviour exactly:
-- no historical figure changes until a user supplies real charges.
--
-- Additive and nullable, so it is safe to run against a live database and
-- safe to re-run (ADD COLUMN IF NOT EXISTS is a no-op the second time).
--
-- Run with, from the repo root:
--     uv run python run_sql_migration.py 011_add_transaction_charges.sql
--
-- That applies it through the app's own DATABASE_URL, so it works on both
-- the MariaDB deployment and Postgres. IF NOT EXISTS on ALTER TABLE needs
-- MariaDB 10.0.2+ or Postgres 9.6+; it is NOT supported on Oracle MySQL,
-- which would need the guarded runner instead.

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS brokerage NUMERIC(20, 4) DEFAULT 0;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS stt NUMERIC(20, 4) DEFAULT 0;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS other_charges NUMERIC(20, 4) DEFAULT 0;

UPDATE transactions SET brokerage = 0 WHERE brokerage IS NULL;
UPDATE transactions SET stt = 0 WHERE stt IS NULL;
UPDATE transactions SET other_charges = 0 WHERE other_charges IS NULL;
