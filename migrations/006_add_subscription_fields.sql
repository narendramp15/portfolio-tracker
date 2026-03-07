-- Migration 006: Add subscription fields to users table and create export_logs table
-- Run once against your PostgreSQL database.

-- Add subscription columns to users (safe: IF NOT EXISTS guards re-runs)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS subscription_tier     VARCHAR(20) NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS subscription_status   VARCHAR(20) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS razorpay_customer_id  VARCHAR(255);

-- Create export_logs table
CREATE TABLE IF NOT EXISTS export_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_export_logs_user_id ON export_logs (user_id);
