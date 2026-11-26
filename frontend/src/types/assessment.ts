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
  status: "PENDING_VIVA" | "IN_VIVA" | "VIVA_COMPLETED" | "SUBMITTED" | "GRADED" | string;
}

export type AIPolicyLevel = "GREEN" | "YELLOW" | "RED";
export type SubmissionType = "FILE_UPLOAD" | "GIT_REPOSITORY" | "HYBRID";
export type MasteryLevelCode = "EXCELLENT" | "GOOD" | "PROFICIENT" | "INSUFFICIENT";

export interface AssignmentSummaryItem {
  id: string;
  course_id: string;
  title: string;
  due_date: string;
  until_date?: string | null;
  late_penalty_percent: number;
  is_viva_required: boolean;
  viva_question_count: number;
  ai_policy_level: AIPolicyLevel | string;
  is_published?: boolean;
  available_from?: string | null;
  max_points?: number;
  max_attempts?: number | null;
  has_rubric?: boolean;
  rubric_is_frozen?: boolean;
  submission_count: number;
  latest_status?: string | null;
}

export interface AssignmentDetail {
  id: string;
  course_id: string;
  title: string;
  instructions: string;
  attachment_url?: string | null;
  submission_type: SubmissionType | string;
  allowed_extensions: string;
  max_file_size_mb: number;
  due_date: string;
  until_date?: string | null;
  late_penalty_percent: number;
  is_viva_required: boolean;
  viva_question_count: number;
  ai_policy_level: AIPolicyLevel | string;
  my_role?: "INSTRUCTOR" | "STUDENT" | string | null;
  is_published?: boolean;
  available_from?: string | null;
  max_points?: number;
  is_group_assignment?: boolean;
  is_transfer_task?: boolean;
  max_attempts?: number | null;
  has_rubric?: boolean;
  rubric_is_frozen?: boolean;
  submissions: Submission[];
}

// ----------------------------------------------------------------------
// Assignment Authoring (T2-P-M3-01)
// ----------------------------------------------------------------------
export interface AssignmentCreateRequest {
  title: string;
  instructions: string;
  attachment_url?: string | null;
  submission_type?: SubmissionType;
  allowed_extensions?: string;
  max_file_size_mb?: number;
  is_group_assignment?: boolean;
  is_transfer_task?: boolean;
  available_from?: string | null;
  due_date: string;
  until_date?: string | null;
  late_penalty_percent?: number;
  is_viva_required?: boolean;
  viva_question_count?: number;
  ai_policy_level?: AIPolicyLevel;
  max_attempts?: number | null;
  publish?: boolean;
}

export interface AssignmentUpdateRequest {
  title?: string;
  instructions?: string;
  attachment_url?: string | null;
  submission_type?: SubmissionType;
  allowed_extensions?: string;
  max_file_size_mb?: number;
  is_group_assignment?: boolean;
  is_transfer_task?: boolean;
  available_from?: string | null;
  due_date?: string;
  until_date?: string | null;
  late_penalty_percent?: number;
  is_viva_required?: boolean;
  viva_question_count?: number;
  ai_policy_level?: AIPolicyLevel;
  max_attempts?: number | null;
}

export interface AssignmentAuthoringResponse {
  id: string;
  course_id: string;
  title: string;
  instructions: string;
  attachment_url?: string | null;
  submission_type: SubmissionType | string;
  allowed_extensions: string;
  max_file_size_mb: number;
  is_group_assignment: boolean;
  is_transfer_task: boolean;
  available_from?: string | null;
  due_date: string;
  until_date?: string | null;
  late_penalty_percent: number;
  is_viva_required: boolean;
  viva_question_count: number;
  ai_policy_level: AIPolicyLevel | string;
  is_published: boolean;
  max_points: number;
  max_attempts?: number | null;
}

export interface AssignmentDeleteResponse {
  id: string;
  deleted: boolean;
}

// ----------------------------------------------------------------------
// Rubric 4 Mastery Levels (T2-P-M3-02)
// ----------------------------------------------------------------------
export interface MasteryLevelItem {
  level: MasteryLevelCode;
  label?: string | null;
  description: string;
  points: number;
}

export interface RubricCriterionPayload {
  title: string;
  description?: string | null;
  lo_id?: string | null;
  competency_code?: string | null;
  max_points: number;
  rating_levels: MasteryLevelItem[];
}

export interface RubricSaveRequest {
  title: string;
  criteria: RubricCriterionPayload[];
}

export interface RubricCriterionResponse {
  id: string;
  title: string;
  description?: string | null;
  lo_id?: string | null;
  competency_code?: string | null;
  max_points: number;
  rating_levels: MasteryLevelItem[];
  order_index: number;
}

export interface RubricResponse {
  assignment_id: string;
  exists: boolean;
  rubric_id?: string | null;
  title?: string | null;
  total_points: number;
  is_frozen: boolean;
  version: number;
  submission_count: number;
  criteria: RubricCriterionResponse[];
}

// ----------------------------------------------------------------------
// Integrity Pledge (T2-P-M3-03)
// ----------------------------------------------------------------------
export interface PledgeTerm {
  code: string;
  text: string;
}

export interface PledgeSignRequest {
  accepted: boolean;
  self_contribution_pct: number;
  tools_used: string[];
  usage_description?: string | null;
}

export interface PledgeStatusResponse {
  assignment_id: string;
  pledge_version: string;
  ai_policy_level: AIPolicyLevel | string;
  terms: PledgeTerm[];
  signed: boolean;
  signed_at?: string | null;
  self_contribution_pct?: number | null;
}

export interface PledgeSignResponse extends PledgeStatusResponse {
  pledge_id: string;
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
  remaining_seconds: number;
  current_question_index: number;
  question: VivaQuestion;
  status: string;
  violation_logs?: VivaViolationLog[];
}

export interface VivaTimeoutRequest {
  question_id?: string;
  answer_text?: string;
  time_spent_seconds?: number;
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

export interface SubmissionReviewSummaryItem {
  id: string;
  assignment_id: string;
  user_id: string;
  student_name: string;
  student_email: string;
  version: number;
  project_title?: string | null;
  file_url?: string | null;
  git_repo_url?: string | null;
  self_contribution_pct: number;
  submitted_at: string;
  is_late: boolean;
  late_penalty_applied: number;
  status: string;
  viva_status?: string | null;
  has_ai_digest: boolean;
  violation_count: number;
}

export interface VivaAnswerEntry {
  answer_text: string;
  time_spent_seconds?: number | null;
  submitted_at?: string | null;
  auto_saved_on_timeout?: boolean;
}

export interface SubmissionReviewDetailResponse {
  submission_id: string;
  assignment_id: string;
  assignment_title: string;
  course_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  version: number;
  project_title?: string | null;
  file_url?: string | null;
  git_repo_url?: string | null;
  comments?: string | null;
  ai_disclosure_data: {
    self_contribution_pct?: number;
    tools_used?: string[];
    usage_description?: string;
    [key: string]: unknown;
  };
  self_contribution_pct: number;
  is_pledge_signed: boolean;
  submitted_at: string;
  is_late: boolean;
  late_penalty_applied: number;
  status: string;
  viva_status?: string | null;
  viva_started_at?: string | null;
  viva_completed_at?: string | null;
  ai_digest_summary?: string | null;
  digest_type?: string | null;
  digest_metadata?: Record<string, unknown>;
  summarizer_mode?: string | null;
  generation_source?: string | null;
  total_questions: number;
  questions: VivaQuestion[];
  answers: Record<string, VivaAnswerEntry>;
  violation_logs: VivaViolationLog[];
}
