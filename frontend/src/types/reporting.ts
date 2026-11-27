/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type ExportFormat = "xlsx" | "csv" | "pdf";

export interface GradeRowPreview {
  user_code: string;
  full_name: string;
  group_scores: Record<string, number | null>;
  total_score: number | null;
  letter_grade: string;
  scale4: number | null;
  hurdle_failed: boolean;
  missing: boolean;
}

export interface LoRowPreview {
  code: string;
  description: string;
  bloom_level: string;
  criterion_titles: string[];
  max_points: number;
}

export interface ExportPreviewResponse {
  course_id: string;
  course_code: string;
  section_code: string;
  course_name: string;
  is_locked: boolean;
  locked_at?: string | null;
  total_students: number;
  missing_grade_students_count: number;
  requires_confirmation: boolean;
  watermark_text?: string | null;
  group_names: string[];
  grade_rows: GradeRowPreview[];
  lo_rows: LoRowPreview[];
  filenames: Record<string, string>;
}
