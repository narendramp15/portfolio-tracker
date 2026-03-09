-- Migration 008: Add options_starter_payment_id to users
-- Stores the Razorpay pay_ID used to activate the Starter tier.
-- UNIQUE constraint prevents the same payment from activating multiple accounts.
-- Run with: psql $DATABASE_URL -f migrations/008_add_starter_payment_id.sql

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS options_starter_payment_id VARCHAR(100);

-- Ensure no two accounts can be activated with the same payment ID
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_options_starter_payment_id
    ON users (options_starter_payment_id)
    WHERE options_starter_payment_id IS NOT NULL;
