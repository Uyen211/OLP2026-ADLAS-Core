-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Additive schema extensions for Phase 3 (T2-P-M3-01..03 Assignment authoring,
-- Rubric Builder and Integrity Pledge; T2-P-M6-03 reporting support indexes).
-- Safe to run multiple times (idempotent via IF NOT EXISTS / DO blocks).

-- ============================================================================
-- 1. Extend assessment.assignments
-- ============================================================================
ALTER TABLE assessment.assignments
    ADD COLUMN IF NOT EXISTS available_from TIMESTAMP WITH TIME ZONE NULL,
    ADD COLUMN IF NOT EXISTS max_points NUMERIC(4, 1) NOT NULL DEFAULT 10.0,
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_by UUID NULL REFERENCES identity.users(id) ON DELETE SET NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_assignment_max_points_positive'
    ) THEN
        ALTER TABLE assessment.assignments
            ADD CONSTRAINT chk_assignment_max_points_positive CHECK (max_points > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_assignment_max_attempts'
    ) THEN
        ALTER TABLE assessment.assignments
            ADD CONSTRAINT chk_assignment_max_attempts
            CHECK (max_attempts IS NULL OR max_attempts >= 1);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_assignment_available_from'
    ) THEN
        ALTER TABLE assessment.assignments
            ADD CONSTRAINT chk_assignment_available_from
            CHECK (available_from IS NULL OR available_from <= due_date);
    END IF;
END $$;

-- ============================================================================
-- 2. Append-only integrity pledge audit table (BR-11, BR-PLG-02)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assessment.integrity_pledges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    pledge_version VARCHAR(30) NOT NULL DEFAULT 'v1.0',
    ai_policy_level VARCHAR(20) NOT NULL,
    self_contribution_pct INTEGER NOT NULL
        CHECK (self_contribution_pct >= 0 AND self_contribution_pct <= 100),
    ai_disclosure_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_ip VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    signed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- UPDATE is forbidden; DELETE is only reachable through FK ON DELETE CASCADE.
CREATE OR REPLACE FUNCTION assessment.prevent_integrity_pledge_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'assessment.integrity_pledges is append-only: UPDATE is not allowed';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_integrity_pledges_no_update ON assessment.integrity_pledges;
CREATE TRIGGER trg_integrity_pledges_no_update
    BEFORE UPDATE ON assessment.integrity_pledges
    FOR EACH ROW EXECUTE FUNCTION assessment.prevent_integrity_pledge_update();

-- ============================================================================
-- 3. Performance indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_assignments_course_published
    ON assessment.assignments (course_id, is_published);

CREATE INDEX IF NOT EXISTS idx_rubric_criteria_lo_id
    ON assessment.rubric_criteria (lo_id);

CREATE INDEX IF NOT EXISTS idx_integrity_pledges_assignment_user
    ON assessment.integrity_pledges (assignment_id, user_id, signed_at DESC);
