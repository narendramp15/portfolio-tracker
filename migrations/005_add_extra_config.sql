-- Migration: Add extra_config column to broker_configs
-- This column stores broker-specific configuration as encrypted JSON

ALTER TABLE broker_configs ADD COLUMN IF NOT EXISTS extra_config TEXT;
