/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export interface AIDisclosure {
  self_contribution_pct: number;
  tools_used: string[];
  usage_description: string;
}

export interface SubmissionCreateRequest {
  project_title?: string;
  file_url?: string;
  file_name?: string;
  git_repo_url?: string;
  comments?: string;
  ai_disclosure: AIDisclosure;
  is_pledge_signed: boolean;
}

export interface Submission {
  id: string;
  assignment_id: string;
  user_id: string;
  version: number;
  project_title?: string | null;
  file_url?: string | null;
  git_repo_url?: string | null;
  comments?: string | null;
  ai_disclosure_data: {
    self_contribution_pct: number;
    tools_used: string[];
    usage_description: string;
    [key: string]: unknown;
  };
  self_contribution_pct: number;
  is_pledge_signed: boolean;
  submitted_at: string;
  is_late: boolean;
  late_penalty_applied: number;
  status: "DRAFT" | "SUBMITTED" | "GRADING" | "GRADED" | string;
}

export interface AssignmentDetail {
  id: string;
  course_id: string;
  title: string;
  instructions: string;
  attachment_url?: string | null;
  submission_type: string;
  allowed_extensions: string;
  max_file_size_mb: number;
  due_date: string;
  until_date?: string | null;
  late_penalty_percent: number;
  is_viva_required: boolean;
  viva_question_count: number;
  submissions: Submission[];
}

export interface VivaQuestion {
  id: string;
  question_index: number;
  total_questions: number;
  question_text: string;
  category: string;
}

export interface VivaViolationLog {
  type: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface VivaStartResponse {
  session_id: string;
  submission_id: string;
  total_questions: number;
  total_duration_seconds: number;
  current_question_index: number;
  question: VivaQuestion;
  status: string;
  violation_logs?: VivaViolationLog[];
}

export interface VivaAnswerSubmitRequest {
  question_id: string;
  answer_text: string;
  time_spent_seconds?: number;
}

export interface VivaAnswerSubmitResponse {
  session_id: string;
  is_completed: boolean;
  next_question?: VivaQuestion | null;
  status: string;
  message: string;
}

export interface VivaSecurityViolationRequest {
  violation_type: "PASTE_ATTEMPT" | "WINDOW_BLUR" | string;
  details?: Record<string, unknown>;
}

export interface PresignedUploadUrlRequest {
  file_name: string;
  content_type: string;
  file_size_bytes: number;
}

export interface PresignedUploadUrlResponse {
  upload_url: string;
  file_url: string;
}
