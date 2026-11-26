/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type GradeItemType = "ASSIGNMENT" | "QUIZ" | "PROGRESS_ATTENDANCE" | "MANUAL";
export type EvidenceFlag = "SUFFICIENT" | "INSUFFICIENT" | "CONFLICTING" | "HUMAN_REVIEW";
export type GradingStatus = "UNGRADED" | "AI_PROPOSED" | "INSTRUCTOR_REVIEWED";
export type PostGradesScope = "ALL" | "GRADED_ONLY";
export type SpeedGraderFilter = "ALL" | "NEEDS_GRADING" | "GRADED" | "CONFLICTING";

export interface GradeColumnItem {
  id: string;
  course_id: string;
  group_id: string;
  item_type: GradeItemType;
  item_id?: string | null;
  title: string;
  max_points: number;
  is_muted: boolean;
}

export interface GradeGroupItem {
  id: string;
  course_id: string;
  group_name: string;
  weight_percent: number;
  drop_lowest_count: number;
  is_hurdle: boolean;
  hurdle_min_score: number;
  columns: GradeColumnItem[];
}

export interface GradebookStructureResponse {
  course_id: string;
  total_weight_percent: number;
  is_weight_valid: boolean;
  is_locked: boolean;
  locked_at?: string | null;
  groups: GradeGroupItem[];
}

export interface GradeGroupInputPayload {
  id?: string;
  group_name: string;
  weight_percent: number;
  drop_lowest_count: number;
  is_hurdle: boolean;
  hurdle_min_score: number;
}

export interface CellGradeDTO {
  column_id: string;
  grade_id?: string | null;
  submission_id?: string | null;
  official_score?: number | null;
  proposed_ai_score?: number | null;
  evidence_flag?: EvidenceFlag | null;
  grading_status: GradingStatus;
  is_muted: boolean;
  is_overridden: boolean;
  instructor_feedback?: string | null;
  voice_feedback_url?: string | null;
}

export interface StudentCourseSummaryRow {
  user_id: string;
  user_code?: string | null;
  full_name: string;
  email: string;
  column_grades: Record<string, CellGradeDTO>;
  group_averages: Record<string, number | null>;
  final_score_10?: number | null;
  letter_grade?: string | null;
  score_4?: number | null;
  is_passed?: boolean | null;
  hurdle_failed: boolean;
  is_provisional: boolean;
  missing_columns_count: number;
}

export interface GradeDistributionBucket {
  label: string;
  range_hint: string;
  count: number;
  percentage: number;
}

export interface ClassGradebookOverviewResponse {
  course_id: string;
  is_locked: boolean;
  locked_at?: string | null;
  locked_by_name?: string | null;
  total_students: number;
  passed_count: number;
  failed_count: number;
  hurdle_failed_count: number;
  incomplete_students_count: number;
  class_average_10?: number | null;
  pass_rate_pct: number;
  fail_rate_pct: number;
  groups: GradeGroupItem[];
  students: StudentCourseSummaryRow[];
  distribution: GradeDistributionBucket[];
}

export interface StudentMyGradeItem {
  column_id: string;
  group_name: string;
  weight_percent: number;
  is_hurdle: boolean;
  title: string;
  item_type: GradeItemType;
  max_points: number;
  is_muted: boolean;
  official_score?: number | null;
  instructor_feedback?: string | null;
  voice_feedback_url?: string | null;
  status_label: string;
}

export interface StudentMyGradesResponse {
  course_id: string;
  is_locked: boolean;
  items: StudentMyGradeItem[];
  final_score_10?: number | null;
  letter_grade?: string | null;
  score_4?: number | null;
  is_passed?: boolean | null;
  hurdle_failed: boolean;
  is_provisional: boolean;
}

export interface CitationItem {
  source_type: "SUBMISSION" | "VIVA";
  reference: string;
  excerpt: string;
}

export interface CriterionProposalItem {
  criterion_id: string;
  criterion_title: string;
  max_points: number;
  proposed_points: number;
  rating_level_label: string;
  explanation: string;
  citations: CitationItem[];
}

export interface RubricProposalResponse {
  submission_id: string;
  evidence_flag: EvidenceFlag;
  proposed_total_score?: number | null;
  summary_comment: string;
  generation_source: string;
  criteria_proposals: CriterionProposalItem[];
}

export interface SpeedGraderSubmissionNavItem {
  submission_id: string;
  user_id: string;
  user_code?: string | null;
  student_name: string;
  student_email: string;
  version: number;
  submitted_at: string;
  is_late: boolean;
  late_penalty_applied: number;
  viva_status?: string | null;
  grading_status: GradingStatus;
  official_score?: number | null;
  proposed_ai_score?: number | null;
  evidence_flag?: EvidenceFlag | null;
}

export interface SpeedGraderSubmissionListResponse {
  assignment_id: string;
  assignment_title: string;
  course_id: string;
  total_submissions: number;
  graded_count: number;
  progress_percent: number;
  items: SpeedGraderSubmissionNavItem[];
}

export interface RubricCriterionView {
  id: string;
  lo_id?: string | null;
  competency_code?: string | null;
  title: string;
  description?: string | null;
  max_points: number;
  order_index: number;
  rating_levels: Array<{
    level?: string;
    label?: string;
    points?: number;
    description?: string;
  }>;
}

export interface SpeedGraderVersionItem {
  submission_id: string;
  version: number;
  submitted_at: string;
  is_late: boolean;
  file_url?: string | null;
  git_repo_url?: string | null;
}

export interface SpeedGraderWorkspaceResponse {
  course_id: string;
  course_name: string;
  assignment_id: string;
  assignment_title: string;
  column_id: string;
  is_gradebook_locked: boolean;
  is_column_muted: boolean;
  submission_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  student_code?: string | null;
  version: number;
  versions: SpeedGraderVersionItem[];
  project_title?: string | null;
  file_url?: string | null;
  git_repo_url?: string | null;
  comments?: string | null;
  self_contribution_pct: number;
  ai_disclosure_data: {
    tools_used?: string[];
    usage_description?: string;
    self_contribution_pct?: number;
  };
  submitted_at: string;
  is_late: boolean;
  late_penalty_applied: number;
  missing_viva: boolean;
  viva_status?: string | null;
  viva_started_at?: string | null;
  viva_completed_at?: string | null;
  ai_digest_summary?: string | null;
  digest_type?: string | null;
  summarizer_mode?: string | null;
  generation_source?: string | null;
  questions: Array<{
    id: string;
    question_index: number;
    total_questions: number;
    question_text: string;
    category?: string;
  }>;
  answers: Record<
    string,
    {
      answer_text?: string;
      time_spent_seconds?: number;
      auto_saved_on_timeout?: boolean;
    }
  >;
  violation_logs: Array<{ type: string; timestamp?: string }>;
  window_blur_count: number;
  paste_attempt_count: number;
  rubric_id?: string | null;
  rubric_title?: string | null;
  rubric_criteria: RubricCriterionView[];
  ai_proposal?: RubricProposalResponse | null;
  grade_id?: string | null;
  official_score?: number | null;
  rubric_scores: Record<string, { points: number; label?: string; lo_id?: string | null }>;
  instructor_feedback?: string | null;
  voice_feedback_url?: string | null;
  is_overridden: boolean;
  grading_status: GradingStatus;
  graded_at?: string | null;
}

export interface VersionDiffLine {
  line_type: "context" | "added" | "removed";
  content: string;
}

export interface VersionDiffResponse {
  v1_submission_id: string;
  v2_submission_id: string;
  v1_version: number;
  v2_version: number;
  summary: string;
  lines: VersionDiffLine[];
}

export interface PostGradesResponse {
  column_id: string;
  is_muted: boolean;
  scope: string;
  published_grades_count: number;
  notification_queued: boolean;
}

export interface GradebookLockPreviewResponse {
  course_id: string;
  is_locked: boolean;
  total_students: number;
  passed_count: number;
  failed_count: number;
  hurdle_failed_count: number;
  pass_rate_pct: number;
  fail_rate_pct: number;
  class_average_10?: number | null;
  muted_columns: string[];
  can_lock: boolean;
}

export interface GradebookLockResponse {
  course_id: string;
  is_locked: boolean;
  locked_at: string;
  locked_by?: string | null;
  locked_by_name?: string | null;
}

export interface GradeAuditLogItem {
  id: string;
  user_id?: string | null;
  action_type: string;
  entity_name: string;
  entity_id: string;
  old_values?: Record<string, unknown> | null;
  new_values?: Record<string, unknown> | null;
  reason?: string | null;
  created_at: string;
}
