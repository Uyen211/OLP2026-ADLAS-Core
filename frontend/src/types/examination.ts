/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type { BloomLevel } from "./course";

export type DecimalValue = number | string;

export type QuestionType = "MULTIPLE_CHOICE" | "MULTI_SELECT";

export type QuizStatus = "DRAFT" | "PUBLISHED" | "CLOSED";

export type SecurityMode = "CONTROLLED" | "REMOTE_PROCTORED" | "PRACTICE";

export type GradeReleasePolicy = "IMMEDIATE" | "AFTER_CLOSE" | "MANUAL";

export type SubmissionStatus =
  | "IN_PROGRESS"
  | "SUBMITTED"
  | "TIMED_OUT"
  | "AUTO_GRADED"
  | "REGRADE_PENDING"
  | "REGRADE_RESOLVED"
  | "FINALIZED";

export type RegradeStatus = "PENDING" | "APPROVED" | "REJECTED";

export type RegradeScope = "SINGLE_STUDENT" | "ENTIRE_CLASS";

export type ExaminationErrorCode =
  | "E-EXAM-03"
  | "E-SEC-01"
  | "E-SEC-02"
  | "E-SEC-03"
  | "E-EXAM-CLOSED"
  | "E-REG-01"
  | "E-13"
  | "E-EXAM-NOT-FOUND"
  | "E-EXAM-FORBIDDEN"
  | "E-EXAM-STATE";

// ------------------------------------------------------------------
// Question Banks
// ------------------------------------------------------------------
export interface QuestionBankCreate {
  category_name: string;
}

export interface QuestionBankResponse {
  id: string;
  course_id: string;
  category_name: string;
  question_count: number;
  created_at: string;
}

// ------------------------------------------------------------------
// Questions
// ------------------------------------------------------------------
export interface QuestionOption {
  id?: string | null;
  key: string;
  text: string;
  is_correct?: boolean;
}

export interface QuestionCreate {
  bank_id: string;
  lo_id?: string | null;
  bloom_level: BloomLevel;
  question_text: string;
  question_type: QuestionType;
  default_points: number;
  options: Array<{
    id?: string | null;
    key: string;
    text: string;
    is_correct: boolean;
  }>;
  explanation?: string | null;
}

export interface QuestionUpdate {
  bank_id?: string;
  lo_id?: string | null;
  bloom_level?: BloomLevel;
  question_text?: string;
  question_type?: QuestionType;
  default_points?: number;
  options?: Array<{
    id?: string | null;
    key: string;
    text: string;
    is_correct: boolean;
  }>;
  explanation?: string | null;
}

export interface QuestionResponse {
  id: string;
  bank_id: string;
  lo_id?: string | null;
  bloom_level: BloomLevel;
  question_text: string;
  question_type: QuestionType;
  default_points: DecimalValue;
  options: QuestionOption[];
  explanation?: string | null;
  is_active: boolean;
  deleted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface QuestionDeleteResponse {
  question_id: string;
  soft_deleted: boolean;
  message: string;
}

// ------------------------------------------------------------------
// Quizzes, Snapshots & Security Room Settings
// ------------------------------------------------------------------
export interface QuizMatrixRule {
  bank_id: string;
  bloom_level?: BloomLevel | null;
  lo_id?: string | null;
  count: number;
}

export interface QuizCreate {
  title: string;
  time_limit_mins: number;
  available_from: string;
  available_until: string;
  passcode?: string | null;
  ip_filter_range?: string | null;
  grade_release_policy: GradeReleasePolicy;
  is_ai_locked: boolean;
  security_mode: SecurityMode;
  max_attempts: number;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  snapshot_mode: boolean;
  matrix_config: QuizMatrixRule[];
  question_ids: string[];
}

export interface QuizSettingsUpdate {
  title?: string | null;
  time_limit_mins: number;
  available_from: string;
  available_until: string;
  passcode?: string | null;
  ip_filter_range?: string | null;
  security_mode: SecurityMode;
  max_attempts: number;
  grade_release_policy: GradeReleasePolicy;
  is_ai_locked: boolean;
  shuffle_questions: boolean;
  shuffle_options: boolean;
}

export interface QuizQuestionSnapshotResponse {
  id: string;
  question_id?: string | null;
  lo_id?: string | null;
  question_order: number;
  question_type: QuestionType;
  question_text_snapshot: string;
  options_snapshot: QuestionOption[];
  explanation_snapshot?: string | null;
  default_points: DecimalValue;
}

export interface QuizSummaryResponse {
  id: string;
  course_id: string;
  title: string;
  status: QuizStatus;
  time_limit_mins: number;
  available_from: string;
  available_until: string;
  security_mode: SecurityMode;
  max_attempts: number;
  grade_release_policy: GradeReleasePolicy;
  grades_published_at?: string | null;
  is_ai_locked: boolean;
  has_passcode: boolean;
  passcode?: string | null;
  ip_filter_range?: string | null;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  snapshot_mode: boolean;
  question_count: number;
  created_at: string;
  updated_at: string;
}

export interface QuizDetailResponse extends QuizSummaryResponse {
  matrix_config: QuizMatrixRule[];
  questions: QuizQuestionSnapshotResponse[];
}

export interface PasscodeRegenerateResponse {
  quiz_id: string;
  passcode: string;
}

export interface PublishGradesResponse {
  quiz_id: string;
  grades_published_at: string;
}

// ------------------------------------------------------------------
// Exam Attempts, Resume Exam & 2-Tier Autosave (T2-P-M4-03)
// ------------------------------------------------------------------
export type StudentAnswerValue = string | string[];
export type StudentAnswersMap = Record<string, StudentAnswerValue>;

export interface AttemptStartRequest {
  passcode?: string | null;
}

export interface AttemptQuestionResponse {
  id: string;
  question_order: number;
  question_type: QuestionType;
  question_text: string;
  options_snapshot: QuestionOption[];
  default_points: DecimalValue;
}

export interface AttemptStartResponse {
  submission_id: string;
  quiz_id: string;
  attempt_number: number;
  resumed: boolean;
  status: SubmissionStatus;
  started_at: string;
  expires_at: string;
  remaining_seconds: number;
  seq_num: number;
  student_answers: StudentAnswersMap;
  flagged_questions: string[];
  security_mode: SecurityMode;
  is_ai_locked: boolean;
  questions: AttemptQuestionResponse[];
}

export interface ViolationEventPayload {
  type: "TAB_BLUR" | "FULLSCREEN_EXIT" | "COPY_PASTE_ATTEMPT" | "CONTEXT_MENU";
  timestamp: string;
  detail?: string;
}

export interface AutosaveRequest {
  seq_num: number;
  answers: StudentAnswersMap;
  flagged_questions?: string[] | null;
  tab_blur_delta?: number;
  fullscreen_exit_delta?: number;
  violation_event?: ViolationEventPayload | null;
}

export interface AutosaveResponse {
  submission_id: string;
  accepted: boolean;
  seq_num: number;
  remaining_seconds: number;
  tab_blur_count: number;
  fullscreen_exit_count: number;
}

export interface SubmitAttemptRequest {
  answers?: StudentAnswersMap | null;
  flagged_questions?: string[] | null;
}

export interface SubmitAttemptResponse {
  submission_id: string;
  quiz_id: string;
  status: SubmissionStatus;
  submitted_at: string;
  grades_visible: boolean;
  auto_score?: DecimalValue | null;
  final_score?: DecimalValue | null;
}

export interface ActiveSessionResponse {
  has_active_session: boolean;
  is_ai_locked: boolean;
  quiz_id: string;
  submission_id?: string | null;
  expires_at?: string | null;
}

// ------------------------------------------------------------------
// Results & 48-Hour Regrade Workflow (T2-P-M4-04)
// ------------------------------------------------------------------
export interface ResultQuestionAnalysis {
  attempt_question_id: string;
  question_order: number;
  question_type: QuestionType;
  question_text: string;
  default_points: DecimalValue;
  earned_points: DecimalValue;
  is_correct: boolean;
  selected_keys: string[];
  correct_keys: string[];
  options_snapshot: QuestionOption[];
  explanation_snapshot?: string | null;
}

export interface RegradeSummaryResponse {
  id: string;
  submission_id: string;
  attempt_question_id?: string | null;
  student_reason: string;
  evidence_url?: string | null;
  regrade_scope: RegradeScope;
  status: RegradeStatus;
  old_score: DecimalValue;
  new_score?: DecimalValue | null;
  reviewer_feedback?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface AttemptResultResponse {
  submission_id: string;
  quiz_id: string;
  quiz_title: string;
  status: SubmissionStatus;
  submitted_at?: string | null;
  grade_release_policy: GradeReleasePolicy;
  grades_visible: boolean;
  release_timestamp?: string | null;
  regrade_deadline?: string | null;
  can_request_regrade: boolean;
  auto_score?: DecimalValue | null;
  final_score?: DecimalValue | null;
  questions: ResultQuestionAnalysis[];
  regrades: RegradeSummaryResponse[];
}

export interface RegradeCreateRequest {
  attempt_question_id: string;
  student_reason: string;
  evidence_url?: string | null;
}

export interface RegradeReviewRequest {
  approved: boolean;
  regrade_scope: RegradeScope;
  new_score?: number | null;
  correct_option_ids?: string[] | null;
  award_full_question_credit: boolean;
  reviewer_feedback: string;
}

export interface RegradeReviewResponse {
  regrade: RegradeSummaryResponse;
  affected_submissions_count: number;
  closed_pending_regrades_count: number;
}

export interface LocalExamDraft {
  submission_id: string;
  quiz_id: string;
  seq_num: number;
  answers: StudentAnswersMap;
  flagged_questions: string[];
  updated_at: string;
}
