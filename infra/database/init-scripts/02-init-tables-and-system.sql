-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT

-- ============================================================================
-- SCRIPT KHOI TAO TOAN BO BANG DU LIEU CHO ADLAS CORE
-- Can cu thiet ke: tailieu/docx/2-de-tai/2-design/data-model.md
-- Bao gom: 7 Bounded Contexts + Schema system (Tang 1 Platform Admin)
-- ============================================================================

-- Bổ sung Schema system cho Tầng 1 Platform Admin
CREATE SCHEMA IF NOT EXISTS system;
COMMENT ON SCHEMA system IS 'Bounded Context for Layer 1 platform administration, system quotas, outbox events, dead-letter queue, and audit logs';

-- ============================================================================
-- 1. SCHEMA identity: Dinh danh, Nguoi dung & Phien lam viec
-- ============================================================================
CREATE TABLE IF NOT EXISTS identity.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(150) NOT NULL UNIQUE,
    user_code VARCHAR(50) UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(255),
    system_role VARCHAR(30) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. SCHEMA system: Quan tri Ha tang Tang 1 (Thanh vien 1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system.system_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    max_slide_mb INTEGER NOT NULL DEFAULT 50 CHECK (max_slide_mb >= 5 AND max_slide_mb <= 100),
    max_video_mb INTEGER NOT NULL DEFAULT 500 CHECK (max_video_mb >= 50 AND max_video_mb <= 1000),
    max_submission_mb INTEGER NOT NULL DEFAULT 25 CHECK (max_submission_mb >= 5 AND max_submission_mb <= 50),
    max_course_storage_gb INTEGER NOT NULL DEFAULT 10 CHECK (max_course_storage_gb >= 1 AND max_course_storage_gb <= 50),
    warning_threshold_pct INTEGER NOT NULL DEFAULT 85 CHECK (warning_threshold_pct >= 50 AND warning_threshold_pct <= 95),
    updated_by UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system.system_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    actor_email VARCHAR(150),
    action VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO' CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS system.dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outbox_event_id UUID REFERENCES system.outbox_events(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    retry_attempts INTEGER NOT NULL DEFAULT 3,
    status VARCHAR(30) NOT NULL DEFAULT 'DEAD_LETTER' CHECK (status IN ('DEAD_LETTER', 'RETRYING', 'RESOLVED')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS system.backup_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_name VARCHAR(200) NOT NULL,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    storage_path VARCHAR(500),
    created_by UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('COMPLETED', 'FAILED'))
);

-- ============================================================================
-- 3. SCHEMA course: Mon hoc, Lop hoc phan & Chuan dau ra (LO)
-- ============================================================================
CREATE TABLE IF NOT EXISTS course.courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(30) NOT NULL,
    section_code VARCHAR(30) NOT NULL,
    name VARCHAR(200) NOT NULL,
    semester VARCHAR(50) NOT NULL,
    credits INTEGER NOT NULL CHECK (credits >= 1 AND credits <= 6),
    grading_scheme VARCHAR(30) NOT NULL DEFAULT 'SCALE_10',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    syllabus_text TEXT,
    join_code VARCHAR(10) UNIQUE,
    is_enrollment_open BOOLEAN NOT NULL DEFAULT TRUE,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(30) NOT NULL DEFAULT 'UNPUBLISHED',
    created_by UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_course_dates CHECK (end_date >= start_date + INTERVAL '7 days'),
    CONSTRAINT uq_course_section_semester UNIQUE (course_code, section_code, semester)
);

CREATE TABLE IF NOT EXISTS course.learning_objectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    code VARCHAR(30) NOT NULL,
    description TEXT NOT NULL,
    bloom_level VARCHAR(30) NOT NULL DEFAULT 'UNDERSTAND',
    order_index INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_course_lo_code UNIQUE (course_id, code)
);

CREATE TABLE IF NOT EXISTS course.course_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    contextual_role VARCHAR(30) NOT NULL,
    enrollment_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_course_user_enrollment UNIQUE (course_id, user_id)
);

CREATE TABLE IF NOT EXISTS course.course_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    group_set_name VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course.course_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES course.course_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_group_member UNIQUE (group_id, user_id)
);

-- ============================================================================
-- 4. SCHEMA learning: Hoc lieu, Video Marker, RAG Vector & Socratic
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning.modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 1,
    unlock_at TIMESTAMP WITH TIME ZONE,
    prerequisite_module_id UUID REFERENCES learning.modules(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning.learning_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID NOT NULL REFERENCES learning.modules(id) ON DELETE CASCADE,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    material_type VARCHAR(30) NOT NULL,
    file_url VARCHAR(500),
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    est_duration_minutes INTEGER DEFAULT 30,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES learning.learning_materials(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    heading_title VARCHAR(255),
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning.material_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES learning.learning_materials(id) ON DELETE CASCADE,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    stop_time_seconds INTEGER,
    section_index INTEGER,
    question_text TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL DEFAULT 'MULTIPLE_CHOICE',
    options JSONB,
    correct_option VARCHAR(10),
    expected_concept TEXT NOT NULL,
    is_blocking BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning.student_material_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES learning.learning_materials(id) ON DELETE CASCADE,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_time_spent_secs INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_user_material_progress UNIQUE (user_id, material_id)
);

CREATE TABLE IF NOT EXISTS learning.socratic_dialogues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    checkpoint_id UUID REFERENCES learning.material_checkpoints(id) ON DELETE SET NULL,
    turn_index INTEGER NOT NULL DEFAULT 1,
    confidence_level VARCHAR(20) CHECK (confidence_level IN ('GUESSING', 'FAIRLY_CONFIDENT', 'VERY_CONFIDENT')),
    student_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    is_concept_mastered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. SCHEMA assessment: Bai tap, Rubric, Khai bao AI & Viva Sandbox
-- ============================================================================
CREATE TABLE IF NOT EXISTS assessment.assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    instructions TEXT NOT NULL,
    attachment_url VARCHAR(500),
    submission_type VARCHAR(50) NOT NULL DEFAULT 'FILE_UPLOAD',
    allowed_extensions VARCHAR(100) NOT NULL DEFAULT '.zip,.pdf,.docx',
    max_file_size_mb INTEGER NOT NULL DEFAULT 50,
    is_group_assignment BOOLEAN NOT NULL DEFAULT FALSE,
    is_transfer_task BOOLEAN NOT NULL DEFAULT FALSE,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    until_date TIMESTAMP WITH TIME ZONE,
    late_penalty_percent NUMERIC(4, 2) NOT NULL DEFAULT 5.0,
    is_viva_required BOOLEAN NOT NULL DEFAULT TRUE,
    viva_question_count INTEGER NOT NULL DEFAULT 3,
    ai_policy_level VARCHAR(20) NOT NULL DEFAULT 'YELLOW',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_assignment_dates CHECK (until_date IS NULL OR until_date >= due_date)
);

CREATE TABLE IF NOT EXISTS assessment.rubrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL UNIQUE REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    total_points NUMERIC(4, 1) NOT NULL DEFAULT 10.0,
    is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment.rubric_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rubric_id UUID NOT NULL REFERENCES assessment.rubrics(id) ON DELETE CASCADE,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    competency_code VARCHAR(20),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    max_points NUMERIC(4, 1) NOT NULL,
    rating_levels JSONB NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS assessment.assignment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL DEFAULT 1,
    file_url VARCHAR(500),
    git_repo_url VARCHAR(500),
    comments TEXT,
    ai_disclosure_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    self_contribution_pct INTEGER NOT NULL CHECK (self_contribution_pct >= 0 AND self_contribution_pct <= 100),
    is_pledge_signed BOOLEAN NOT NULL DEFAULT TRUE,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    late_penalty_applied NUMERIC(4, 2) NOT NULL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_VIVA',
    CONSTRAINT uq_assignment_user_version UNIQUE (assignment_id, user_id, version)
);

CREATE TABLE IF NOT EXISTS assessment.viva_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL UNIQUE REFERENCES assessment.assignment_submissions(id) ON DELETE CASCADE,
    questions_answers JSONB NOT NULL,
    violation_logs JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED'
);

-- ============================================================================
-- 6. SCHEMA examination: Ngan hang De, Phong thi Autosave & Phuc khao
-- ============================================================================
CREATE TABLE IF NOT EXISTS examination.question_banks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    category_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS examination.questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_id UUID NOT NULL REFERENCES examination.question_banks(id) ON DELETE CASCADE,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL DEFAULT 'MULTIPLE_CHOICE',
    default_points NUMERIC(4, 2) NOT NULL DEFAULT 1.0,
    options JSONB NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS examination.quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    time_limit_mins INTEGER NOT NULL DEFAULT 45,
    available_from TIMESTAMP WITH TIME ZONE NOT NULL,
    available_until TIMESTAMP WITH TIME ZONE NOT NULL,
    passcode VARCHAR(50),
    ip_filter_range VARCHAR(100),
    grade_release_policy VARCHAR(30) NOT NULL DEFAULT 'AFTER_CLOSE',
    is_ai_locked BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_quiz_availability CHECK (available_until > available_from)
);

CREATE TABLE IF NOT EXISTS examination.quiz_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES examination.quizzes(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    student_answers JSONB NOT NULL DEFAULT '{}'::jsonb,
    auto_score NUMERIC(4, 2),
    final_score NUMERIC(4, 2),
    client_ip VARCHAR(45),
    tab_blur_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_PROGRESS',
    CONSTRAINT uq_quiz_user_submission UNIQUE (quiz_id, user_id)
);

CREATE TABLE IF NOT EXISTS examination.quiz_attempt_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES examination.quiz_submissions(id) ON DELETE CASCADE,
    question_id UUID REFERENCES examination.questions(id) ON DELETE SET NULL,
    lo_id UUID REFERENCES course.learning_objectives(id) ON DELETE SET NULL,
    question_order INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    options_snapshot JSONB NOT NULL,
    default_points NUMERIC(4, 2) NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS examination.quiz_regrades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL UNIQUE REFERENCES examination.quiz_submissions(id) ON DELETE CASCADE,
    student_reason TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    old_score NUMERIC(4, 2) NOT NULL,
    new_score NUMERIC(4, 2),
    reviewer_feedback TEXT,
    reviewed_by UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 7. SCHEMA gradebook: So diem Dong, SpeedGrader & Khoa So Poka-yoke
-- ============================================================================
CREATE TABLE IF NOT EXISTS gradebook.gradebook_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    group_name VARCHAR(100) NOT NULL,
    weight_percent INTEGER NOT NULL CHECK (weight_percent >= 1 AND weight_percent <= 100),
    drop_lowest_count INTEGER NOT NULL DEFAULT 0,
    is_hurdle BOOLEAN NOT NULL DEFAULT FALSE,
    hurdle_min_score NUMERIC(4, 2) DEFAULT 4.0
);

CREATE TABLE IF NOT EXISTS gradebook.gradebook_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES gradebook.gradebook_groups(id) ON DELETE RESTRICT,
    item_type VARCHAR(30) NOT NULL,
    item_id UUID,
    title VARCHAR(150) NOT NULL,
    max_points NUMERIC(4, 2) NOT NULL DEFAULT 10.0,
    is_muted BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS gradebook.grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id UUID NOT NULL REFERENCES gradebook.gradebook_columns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
    proposed_ai_score NUMERIC(4, 2),
    proposed_ai_citations JSONB,
    official_score NUMERIC(4, 2) CHECK (official_score >= 0.0 AND official_score <= 10.0),
    rubric_scores JSONB,
    instructor_feedback TEXT,
    voice_feedback_url VARCHAR(500),
    annotations JSONB,
    is_overridden BOOLEAN NOT NULL DEFAULT FALSE,
    graded_by UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    graded_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_column_user_grade UNIQUE (column_id, user_id)
);

CREATE TABLE IF NOT EXISTS gradebook.course_gradebook_locks (
    course_id UUID PRIMARY KEY REFERENCES course.courses(id) ON DELETE CASCADE,
    is_locked BOOLEAN NOT NULL DEFAULT TRUE,
    locked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    locked_by UUID REFERENCES identity.users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS gradebook.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 8. SCHEMA analytics: Chan doan Diem mu & Báo cáo
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics.class_diagnostics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    lo_id UUID NOT NULL REFERENCES course.learning_objectives(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    struggle_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    top_misconceptions JSONB DEFAULT '[]'::jsonb,
    at_risk_student_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
