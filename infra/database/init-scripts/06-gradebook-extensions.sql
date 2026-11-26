-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Additive schema extensions for Phase 3 Gradebook & SpeedGrader
-- (T2-P-M5-01, T2-P-M5-02, T2-I-M5-03, T2-P-M5-04, T2-P-M5-05).
-- Idempotent: safe to run multiple times on existing databases.

-- 1. Extend gradebook.grades with AI proposal metadata, evidence flag, and status
ALTER TABLE gradebook.grades
    ADD COLUMN IF NOT EXISTS submission_id UUID NULL REFERENCES assessment.assignment_submissions(id) ON DELETE SET NULL;

ALTER TABLE gradebook.grades
    ADD COLUMN IF NOT EXISTS evidence_flag VARCHAR(30) NULL;

ALTER TABLE gradebook.grades
    ADD COLUMN IF NOT EXISTS ai_proposed_details JSONB NULL;

ALTER TABLE gradebook.grades
    ADD COLUMN IF NOT EXISTS grading_status VARCHAR(30) NOT NULL DEFAULT 'UNGRADED';

ALTER TABLE gradebook.grades
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();

-- 2. Extend gradebook.course_gradebook_locks for emergency unlock audit (Subflow A-1)
ALTER TABLE gradebook.course_gradebook_locks
    ADD COLUMN IF NOT EXISTS unlock_decision_code VARCHAR(100) NULL;

ALTER TABLE gradebook.course_gradebook_locks
    ADD COLUMN IF NOT EXISTS unlock_reason TEXT NULL;

ALTER TABLE gradebook.course_gradebook_locks
    ADD COLUMN IF NOT EXISTS unlocked_at TIMESTAMP WITH TIME ZONE NULL;

ALTER TABLE gradebook.course_gradebook_locks
    ADD COLUMN IF NOT EXISTS unlocked_by UUID NULL REFERENCES identity.users(id) ON DELETE SET NULL;

-- 3. Prevent duplicate synced columns for the same assignment/quiz in a course
CREATE UNIQUE INDEX IF NOT EXISTS uq_gradebook_col_course_item
    ON gradebook.gradebook_columns (course_id, item_type, item_id)
    WHERE item_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gradebook_grades_column_user
    ON gradebook.grades (column_id, user_id);

CREATE INDEX IF NOT EXISTS idx_gradebook_grades_submission
    ON gradebook.grades (submission_id)
    WHERE submission_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gradebook_audit_entity
    ON gradebook.audit_logs (entity_name, entity_id, created_at DESC);

-- 4. Physical Sealing Trigger (BR-12 / E-14):
-- Blocks INSERT/UPDATE/DELETE on gradebook.grades when course gradebook is permanently locked,
-- unless session GUC 'adlas.emergency_unlock_active' is explicitly set to 'true' in a transaction.
CREATE OR REPLACE FUNCTION gradebook.fn_guard_locked_grades()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_column_id UUID;
    v_course_id UUID;
    v_is_locked BOOLEAN;
    v_emergency_active TEXT;
BEGIN
    v_emergency_active := current_setting('adlas.emergency_unlock_active', true);
    IF v_emergency_active = 'true' THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_column_id := OLD.column_id;
    ELSE
        v_column_id := NEW.column_id;
    END IF;

    SELECT c.course_id INTO v_course_id
    FROM gradebook.gradebook_columns c
    WHERE c.id = v_column_id;

    IF v_course_id IS NOT NULL THEN
        SELECT l.is_locked INTO v_is_locked
        FROM gradebook.course_gradebook_locks l
        WHERE l.course_id = v_course_id;

        IF COALESCE(v_is_locked, FALSE) = TRUE THEN
            RAISE EXCEPTION 'GRADEBOOK_IS_PERMANENTLY_LOCKED: Course % gradebook is sealed.', v_course_id
                USING ERRCODE = 'P0001';
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_locked_grade_mutation ON gradebook.grades;
CREATE TRIGGER trg_prevent_locked_grade_mutation
    BEFORE INSERT OR UPDATE OR DELETE ON gradebook.grades
    FOR EACH ROW
    EXECUTE FUNCTION gradebook.fn_guard_locked_grades();
