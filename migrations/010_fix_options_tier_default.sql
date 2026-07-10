-- Migration 010: Correct the unintended 'starter' grant from migration 007.
-- Migration 007 originally created options_tier with DEFAULT 'starter', which
-- silently gave every pre-existing user the paid Starter tier. Reset those rows
-- to 'free' EXCEPT users who genuinely activated Starter (they have a recorded
-- options_starter_payment_id), so real paid activations are preserved.
-- Run with: psql $DATABASE_URL -f migrations/010_fix_options_tier_default.sql

ALTER TABLE users ALTER COLUMN options_tier SET DEFAULT 'free';

UPDATE users
SET options_tier = 'free'
WHERE options_tier = 'starter'
  AND options_starter_payment_id IS NULL;
