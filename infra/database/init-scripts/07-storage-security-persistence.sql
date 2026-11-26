-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Persistent security tables replacing volatile in-memory state:
-- 1. identity.revoked_tokens: persistent JWT blacklist across restarts (T1-C-M0-01)
-- 2. system.gateway_ip_whitelist: persistent exam room CIDR whitelist (T1-A-M0-02)
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS identity.revoked_tokens (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id UUID NULL REFERENCES identity.users(id) ON DELETE SET NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires
    ON identity.revoked_tokens (expires_at);

CREATE TABLE IF NOT EXISTS system.gateway_ip_whitelist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cidr VARCHAR(64) NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_by VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gateway_ip_whitelist_active
    ON system.gateway_ip_whitelist (is_active, created_at DESC);
