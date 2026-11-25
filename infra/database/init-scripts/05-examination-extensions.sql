-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Additive schema extensions for Phase 2 (Module 4: Examination & CBT Engine).
-- Supports 2-tier immutable snapshots (quiz_questions + quiz_attempt_questions),
-- soft delete for snapshotted questions, multi-attempt practice mode,
-- monotonic autosave seq_num, violation logs, grade release timestamps,
-- and per-question / entire-class 48h regrade workflows.
-- Safe to run multiple times (idempotent via IF NOT EXISTS / DO blocks).

-- ============================================================================
-- 1. Extend examination.questions (Bloom taxonomy & Soft Delete metadata)
-- ============================================================================
ALTER TABLE examination.questions
    ADD COLUMN IF NOT EXISTS bloom_level VARCHAR(30) NOT NULL DEFAULT 'UNDERSTAND',
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_question_points_positive'
    ) THEN
        ALTER TABLE examination.questions
            ADD CONSTRAINT chk_exam_question_points_positive
            CHECK (default_points > 0);
    END IF;
END $$;

-- ============================================================================
-- 2. Extend examination.quizzes (Lifecycle, Security Mode, Matrix, Release)
-- ============================================================================
ALTER TABLE examination.quizzes
    ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS security_mode VARCHAR(30) NOT NULL DEFAULT 'CONTROLLED',
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS shuffle_questions BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS shuffle_options BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS snapshot_mode BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS matrix_config JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS grades_published_at TIMESTAMP WITH TIME ZONE NULL,
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_quiz_status'
    ) THEN
        ALTER TABLE examination.quizzes
            ADD CONSTRAINT chk_exam_quiz_status
            CHECK (status IN ('DRAFT', 'PUBLISHED', 'CLOSED'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_quiz_security_mode'
    ) THEN
        ALTER TABLE examination.quizzes
            ADD CONSTRAINT chk_exam_quiz_security_mode
            CHECK (security_mode IN ('CONTROLLED', 'REMOTE_PROCTORED', 'PRACTICE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_quiz_grade_release_policy'
    ) THEN
        ALTER TABLE examination.quizzes
            ADD CONSTRAINT chk_exam_quiz_grade_release_policy
            CHECK (grade_release_policy IN ('IMMEDIATE', 'AFTER_CLOSE', 'MANUAL'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_quiz_time_limit_positive'
    ) THEN
        ALTER TABLE examination.quizzes
            ADD CONSTRAINT chk_exam_quiz_time_limit_positive
            CHECK (time_limit_mins > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_quiz_max_attempts_positive'
    ) THEN
        ALTER TABLE examination.quizzes
            ADD CONSTRAINT chk_exam_quiz_max_attempts_positive
            CHECK (max_attempts >= 1);
    END IF;
END $$;

-- ============================================================================
-- 3. Create examination.quiz_questions (Tier-1 Quiz-level Frozen Snapshot)
-- ============================================================================
CREATE TABLE IF NOT EXISTS examination.quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES examination.quizzes(id) ON DELETE CASCADE,
    question_id UUID REFERENCES examination.questions(id) ON DELETE SET NULL,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    question_order INTEGER NOT NULL,
    question_type VARCHAR(30) NOT NULL DEFAULT 'MULTIPLE_CHOICE',
    question_text_snapshot TEXT NOT NULL,
    options_snapshot JSONB NOT NULL,
    explanation_snapshot TEXT,
    default_points NUMERIC(4, 2) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_quiz_question_order UNIQUE (quiz_id, question_order),
    CONSTRAINT chk_quiz_question_points_positive CHECK (default_points > 0)
);

-- ============================================================================
-- 4. Extend examination.quiz_submissions (Attempts, Autosave seq_num, Violations)
-- ============================================================================
ALTER TABLE examination.quiz_submissions
    ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS seq_num INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE NULL,
    ADD COLUMN IF NOT EXISTS flagged_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS fullscreen_exit_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS violation_logs JSONB NOT NULL DEFAULT '[]'::jsonb;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_quiz_user_submission'
          AND conrelid = 'examination.quiz_submissions'::regclass
    ) THEN
        ALTER TABLE examination.quiz_submissions
            DROP CONSTRAINT uq_quiz_user_submission;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_quiz_user_attempt'
          AND conrelid = 'examination.quiz_submissions'::regclass
    ) THEN
        ALTER TABLE examination.quiz_submissions
            ADD CONSTRAINT uq_quiz_user_attempt UNIQUE (quiz_id, user_id, attempt_number);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_submission_attempt_positive'
    ) THEN
        ALTER TABLE examination.quiz_submissions
            ADD CONSTRAINT chk_exam_submission_attempt_positive
            CHECK (attempt_number >= 1);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_submission_seq_non_negative'
    ) THEN
        ALTER TABLE examination.quiz_submissions
            ADD CONSTRAINT chk_exam_submission_seq_non_negative
            CHECK (seq_num >= 0);
    END IF;
END $$;

-- ============================================================================
-- 5. Extend examination.quiz_attempt_questions (Tier-2 Per-student Snapshot)
-- ============================================================================
ALTER TABLE examination.quiz_attempt_questions
    ADD COLUMN IF NOT EXISTS quiz_question_id UUID REFERENCES examination.quiz_questions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS question_type VARCHAR(30) NOT NULL DEFAULT 'MULTIPLE_CHOICE',
    ADD COLUMN IF NOT EXISTS explanation_snapshot TEXT NULL;

-- ============================================================================
-- 6. Extend examination.quiz_regrades (Per-question & Entire-class Regrade)
-- ============================================================================
ALTER TABLE examination.quiz_regrades
    ADD COLUMN IF NOT EXISTS attempt_question_id UUID REFERENCES examination.quiz_attempt_questions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS evidence_url VARCHAR(500) NULL,
    ADD COLUMN IF NOT EXISTS regrade_scope VARCHAR(30) NOT NULL DEFAULT 'SINGLE_STUDENT';

DO $$
DECLARE
    old_uq_name TEXT;
BEGIN
    -- Drop legacy single-column UNIQUE (submission_id) constraint if present
    SELECT c.conname INTO old_uq_name
    FROM pg_constraint c
    JOIN pg_attribute a
      ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
    WHERE c.conrelid = 'examination.quiz_regrades'::regclass
      AND c.contype = 'u'
      AND array_length(c.conkey, 1) = 1
      AND a.attname = 'submission_id'
    LIMIT 1;

    IF old_uq_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE examination.quiz_regrades DROP CONSTRAINT %I', old_uq_name);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_quiz_regrade_submission_question'
          AND conrelid = 'examination.quiz_regrades'::regclass
    ) THEN
        ALTER TABLE examination.quiz_regrades
            ADD CONSTRAINT uq_quiz_regrade_submission_question
            UNIQUE (submission_id, attempt_question_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_exam_regrade_scope'
    ) THEN
        ALTER TABLE examination.quiz_regrades
            ADD CONSTRAINT chk_exam_regrade_scope
            CHECK (regrade_scope IN ('SINGLE_STUDENT', 'ENTIRE_CLASS'));
    END IF;
END $$;

-- ============================================================================
-- 7. Performance Indexes for Examination Context
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_exam_question_banks_course_id
    ON examination.question_banks (course_id);

CREATE INDEX IF NOT EXISTS idx_exam_questions_bank_id
    ON examination.questions (bank_id);

CREATE INDEX IF NOT EXISTS idx_exam_questions_lo_id
    ON examination.questions (lo_id);

CREATE INDEX IF NOT EXISTS idx_exam_questions_active_bloom
    ON examination.questions (bank_id, bloom_level)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_exam_quizzes_course_id
    ON examination.quizzes (course_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_questions_quiz_id
    ON examination.quiz_questions (quiz_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_questions_question_id
    ON examination.quiz_questions (question_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_questions_lo_id
    ON examination.quiz_questions (lo_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_submissions_quiz_user
    ON examination.quiz_submissions (quiz_id, user_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_attempt_questions_submission_id
    ON examination.quiz_attempt_questions (submission_id);

CREATE INDEX IF NOT EXISTS idx_exam_quiz_regrades_submission_id
    ON examination.quiz_regrades (submission_id);
