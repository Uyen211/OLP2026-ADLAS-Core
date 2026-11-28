-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT

-- Migration: 07-tv3-milestones-groups-exam-extensions.sql
-- Description: Schema extensions for assessment milestones, project groups,
--              peer reviews, question folders, and examination proctoring.

-- 1. Assessment schema extensions
ALTER TABLE assessment.assignments
    ADD COLUMN IF NOT EXISTS assignment_type VARCHAR(20) NOT NULL DEFAULT 'INDIVIDUAL',
    ADD COLUMN IF NOT EXISTS group_min_size INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS group_max_size INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS group_formation_deadline TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS grade_group_id UUID;

CREATE TABLE IF NOT EXISTS assessment.assignment_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    due_date TIMESTAMPTZ NOT NULL,
    until_date TIMESTAMPTZ,
    weight_percent NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    sort_order INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assignment_milestones_assignment_id
    ON assessment.assignment_milestones(assignment_id);

CREATE TABLE IF NOT EXISTS assessment.project_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    max_groups_per_topic INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_topics_assignment_id
    ON assessment.project_topics(assignment_id);

CREATE TABLE IF NOT EXISTS assessment.student_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES assessment.project_topics(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    leader_id UUID NOT NULL REFERENCES identity.users(id),
    join_code VARCHAR(10) NOT NULL,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_student_groups_assignment_id
    ON assessment.student_groups(assignment_id);
CREATE INDEX IF NOT EXISTS idx_student_groups_topic_id
    ON assessment.student_groups(topic_id);

CREATE TABLE IF NOT EXISTS assessment.group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES assessment.student_groups(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES identity.users(id),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_assignment_student_membership UNIQUE (group_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_group_members_student_id
    ON assessment.group_members(student_id);

CREATE TABLE IF NOT EXISTS assessment.peer_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assessment.assignments(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES assessment.student_groups(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES identity.users(id),
    reviewee_id UUID NOT NULL REFERENCES identity.users(id),
    contribution_score NUMERIC(5, 2) NOT NULL,
    comment TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_peer_review_pair UNIQUE (assignment_id, reviewer_id, reviewee_id),
    CONSTRAINT chk_peer_score CHECK (contribution_score >= 0 AND contribution_score <= 100)
);

CREATE INDEX IF NOT EXISTS idx_peer_reviews_assignment_group
    ON assessment.peer_reviews(assignment_id, group_id);

ALTER TABLE assessment.assignment_submissions
    ADD COLUMN IF NOT EXISTS milestone_id UUID REFERENCES assessment.assignment_milestones(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES assessment.student_groups(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS github_commit_sha VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_submissions_milestone_id
    ON assessment.assignment_submissions(milestone_id);
CREATE INDEX IF NOT EXISTS idx_submissions_group_id
    ON assessment.assignment_submissions(group_id);

-- 2. Examination schema extensions
CREATE TABLE IF NOT EXISTS examination.question_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES course.courses(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES examination.question_folders(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_question_folders_course_id
    ON examination.question_folders(course_id);
CREATE INDEX IF NOT EXISTS idx_question_folders_parent_id
    ON examination.question_folders(parent_id);

ALTER TABLE examination.questions
    ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES examination.question_folders(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS difficulty VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    ADD COLUMN IF NOT EXISTS source_ref VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_questions_folder_id
    ON examination.questions(folder_id);

ALTER TABLE examination.quizzes
    ADD COLUMN IF NOT EXISTS grade_group_id UUID,
    ADD COLUMN IF NOT EXISTS grade_multiplier INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS selection_mode VARCHAR(30) NOT NULL DEFAULT 'FIXED',
    ADD COLUMN IF NOT EXISTS draw_rules_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS strict_mode_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS max_strikes INT NOT NULL DEFAULT 3;

ALTER TABLE examination.quiz_submissions
    ADD COLUMN IF NOT EXISTS strike_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS violation_logs_json JSONB NOT NULL DEFAULT '[]'::jsonb;
