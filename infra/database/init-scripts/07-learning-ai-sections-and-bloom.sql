-- Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
-- SPDX-License-Identifier: MIT

-- ============================================================================
-- Migration 07: AI Section Extraction Cache & Bloom/Citation on Checkpoints
-- Task: T2-I-M2-04
-- ============================================================================

-- 1. Add JSONB sections_cache to learning.learning_materials (Option 1B)
ALTER TABLE learning.learning_materials
    ADD COLUMN IF NOT EXISTS sections_cache JSONB;

-- 2. Add bloom_level and source_citation to learning.material_checkpoints (Option 2A)
ALTER TABLE learning.material_checkpoints
    ADD COLUMN IF NOT EXISTS bloom_level VARCHAR(20),
    ADD COLUMN IF NOT EXISTS source_citation TEXT;
