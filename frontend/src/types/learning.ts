/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type MaterialType = "SLIDE" | "PDF" | "VIDEO" | "DOCUMENT";

export interface LearningMaterial {
  id: string;
  module_id: string;
  lo_id?: string | null;
  lo_code?: string | null;
  title: string;
  material_type: MaterialType;
  file_url?: string | null;
  is_mandatory: boolean;
  est_duration_minutes: number;
  is_published: boolean;
  created_at: string;
}

export interface LearningModule {
  id: string;
  course_id: string;
  title: string;
  order_index: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  prerequisite_title?: string | null;
  is_published: boolean;
  is_locked: boolean;
  lock_reason?: string | null;
  created_at: string;
  materials: LearningMaterial[];
}

export interface ModuleCreatePayload {
  title: string;
  order_index?: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  is_published?: boolean;
}

export interface ModuleUpdatePayload {
  title?: string;
  order_index?: number;
  unlock_at?: string | null;
  prerequisite_module_id?: string | null;
  is_published?: boolean;
}

export interface MaterialCreatePayload {
  title: string;
  material_type: MaterialType;
  lo_id?: string | null;
  file_url?: string | null;
  is_mandatory?: boolean;
  est_duration_minutes?: number;
  is_published?: boolean;
}

export interface MaterialUpdatePayload {
  title?: string;
  material_type?: MaterialType;
  lo_id?: string | null;
  file_url?: string | null;
  is_mandatory?: boolean;
  est_duration_minutes?: number;
  is_published?: boolean;
}

export interface MaterialUploadResult {
  file_url: string;
  file_name: string;
  size_bytes: number;
  material_type: MaterialType;
}

export interface MaterialCheckpoint {
  id: string;
  material_id: string;
  lo_id?: string | null;
  stop_time_seconds?: number | null;
  section_index?: number | null;
  question_text: string;
  question_type: string;
  options?: Record<string, string> | null;
  correct_option?: string | null;
  expected_concept?: string | null;
  is_blocking: boolean;
  time_limit_seconds: number;
  rewind_seconds: number;
  is_passed?: boolean;
  created_at: string;
}

export interface CheckpointCreatePayload {
  question_text: string;
  question_type?: string;
  stop_time_seconds?: number | null;
  section_index?: number | null;
  options: Record<string, string>;
  correct_option: string;
  expected_concept?: string | null;
  is_blocking?: boolean;
  time_limit_seconds?: number;
  rewind_seconds?: number;
  lo_id?: string | null;
  bloom_level?: "REMEMBER" | "UNDERSTAND" | "APPLY";
  source_citation?: string | null;
}

export interface CheckpointUpdatePayload {
  question_text?: string;
  stop_time_seconds?: number | null;
  section_index?: number | null;
  options?: Record<string, string>;
  correct_option?: string;
  expected_concept?: string | null;
  is_blocking?: boolean;
  time_limit_seconds?: number;
  rewind_seconds?: number;
  lo_id?: string | null;
  bloom_level?: "REMEMBER" | "UNDERSTAND" | "APPLY";
  source_citation?: string | null;
}

export interface CheckpointSubmitResult {
  checkpoint_id: string;
  is_correct: boolean;
  is_passed: boolean;
  rewind_seconds: number;
  message: string;
}

export interface MaterialPageItem {
  index: number;
  title: string;
  content_lines: string[];
  image_url?: string | null;
}

export interface MaterialStructuredContent {
  material_id: string;
  content_kind: "PDF_PAGES" | "SLIDE_DECK" | "DOC_SECTIONS" | "UNSUPPORTED";
  total_items: number;
  items: MaterialPageItem[];
}

export interface DocumentSection {
  section_id: number;
  title: string;
  start_page: number;
  end_page: number;
  word_count: number;
  summary: string;
}

export interface MaterialSectionsResponse {
  material_id: string;
  total_pages: number;
  sections: DocumentSection[];
}

export interface GenerateCheckpointSuggestionsRequest {
  section_ids: number[];
  bloom_level: "REMEMBER" | "UNDERSTAND" | "APPLY";
  num_questions: number;
  lo_id?: string | null;
}

export interface CheckpointSuggestion {
  temp_id: string;
  question_text: string;
  options: Record<string, string>;
  correct_option: string;
  bloom_level: "REMEMBER" | "UNDERSTAND" | "APPLY";
  lo_id?: string | null;
  citation_page: number;
  citation_paragraph: number;
  citation: string;
  evidence_quote: string;
}
