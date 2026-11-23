-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Additive schema extensions for Phase 1 (T2-P-M1-01 MFA & T2-P-M1-02 LO metadata).
-- Safe to run multiple times (idempotent via IF NOT EXISTS).

ALTER TABLE identity.users
    ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(64) NULL;

ALTER TABLE course.learning_objectives
    ADD COLUMN IF NOT EXISTS detail_description TEXT NULL,
    ADD COLUMN IF NOT EXISTS weight_percent NUMERIC(5, 2) NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_lo_weight_percent'
    ) THEN
        ALTER TABLE course.learning_objectives
            ADD CONSTRAINT chk_lo_weight_percent
            CHECK (weight_percent IS NULL OR (weight_percent >= 0 AND weight_percent <= 100));
    END IF;
END $$;
