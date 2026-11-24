-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT
--
-- Additive schema extensions for Phase 2 (T2-P-M3-04 & T2-I-M3-05).
-- Safe to run multiple times (idempotent via IF NOT EXISTS).

ALTER TABLE assessment.assignment_submissions
    ADD COLUMN IF NOT EXISTS project_title VARCHAR(255) NULL;
