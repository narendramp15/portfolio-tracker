-- Migration 009: Record processed Razorpay payments to prevent replay/reuse.
-- Backs verify_options_credits_payment idempotency (billing.py).
-- Run with: psql $DATABASE_URL -f migrations/009_add_processed_payments.sql

CREATE TABLE IF NOT EXISTS processed_payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_id VARCHAR(100) NOT NULL UNIQUE,
    order_id VARCHAR(100),
    purpose VARCHAR(40) NOT NULL,
    pack_id VARCHAR(40),
    amount_paise INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_processed_payments_user_id ON processed_payments (user_id);
