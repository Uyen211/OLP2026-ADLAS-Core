-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT

-- Create 7 Bounded Context Schemas
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS course;
CREATE SCHEMA IF NOT EXISTS learning;
CREATE SCHEMA IF NOT EXISTS assessment;
CREATE SCHEMA IF NOT EXISTS examination;
CREATE SCHEMA IF NOT EXISTS gradebook;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

COMMENT ON SCHEMA identity IS 'Bounded Context for user identity, authentication, and role assignments';
COMMENT ON SCHEMA course IS 'Bounded Context for syllabus, course templates, learning objectives, and enrollment';
COMMENT ON SCHEMA learning IS 'Bounded Context for learning materials, video checkpoints, and socratic dialogue';
COMMENT ON SCHEMA assessment IS 'Bounded Context for assignments, rubrics, submissions, and viva defense sandbox';
COMMENT ON SCHEMA examination IS 'Bounded Context for question bank, snapshot exams, and autosave sessions';
COMMENT ON SCHEMA gradebook IS 'Bounded Context for dynamic gradebook, hurdle calculations, and speedgrader audits';
COMMENT ON SCHEMA analytics IS 'Bounded Context for student competency radar profiles and class knowledge gap heatmap';
