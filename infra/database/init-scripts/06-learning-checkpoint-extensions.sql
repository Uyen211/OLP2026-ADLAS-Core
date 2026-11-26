-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT

-- ============================================================================
-- Migration 06: Learning Checkpoint Extensions & Student Attempt Tracking
-- ============================================================================

-- 1. Extend learning.material_checkpoints with countdown & rewind settings
ALTER TABLE learning.material_checkpoints
    ADD COLUMN IF NOT EXISTS time_limit_seconds INTEGER NOT NULL DEFAULT 10,
    ADD COLUMN IF NOT EXISTS rewind_seconds INTEGER NOT NULL DEFAULT 15;

-- 2. Track student attempts and pass status per checkpoint
CREATE TABLE IF NOT EXISTS learning.student_checkpoint_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    checkpoint_id UUID NOT NULL REFERENCES learning.material_checkpoints(id) ON DELETE CASCADE,
    selected_option VARCHAR(10),
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    passed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_checkpoint_attempt UNIQUE (user_id, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_student_checkpoint_user
    ON learning.student_checkpoint_attempts(user_id, checkpoint_id);
