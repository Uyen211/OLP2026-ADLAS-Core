/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export type CourseStatus =
  | "UNPUBLISHED"
  | "PUBLISHED"
  | "ENROLLMENT_CLOSED"
  | "ARCHIVED";

export type ContextualRole = "INSTRUCTOR" | "STUDENT" | "TA";

export type EnrollmentStatus = "ACTIVE" | "DROPPED" | "COMPLETED";

export type BloomLevel =
  | "REMEMBER"
  | "UNDERSTAND"
  | "APPLY"
  | "ANALYZE"
  | "EVALUATE"
  | "CREATE";

export type GroupingMode = "RANDOM" | "SELF_SIGNUP" | "MANUAL";

export type RosterRowStatus =
  | "VALID"
  | "DUPLICATE_IN_COURSE"
  | "DUPLICATE_IN_FILE"
  | "INVALID";

export interface LOResponse {
  id: string;
  course_id: string;
  code: string;
  description: string;
  bloom_level: BloomLevel;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface LOCreate {
  code: string;
  description: string;
  bloom_level: BloomLevel;
}

export interface LOUpdate {
  code?: string;
  description?: string;
  bloom_level?: BloomLevel;
}

export interface CourseSummary {
  id: string;
  course_code: string;
  section_code: string;
  name: string;
  semester: string;
  credits: number;
  start_date: string;
  end_date: string;
  is_template: boolean;
  is_enrollment_open: boolean;
  status: CourseStatus;
  my_role?: ContextualRole | null;
  student_count: number;
  lo_count: number;
}

export interface CourseDetail extends CourseSummary {
  grading_scheme: string;
  syllabus_text?: string | null;
  join_code?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  learning_objectives: LOResponse[];
}

export interface CourseCreate {
  course_code: string;
  section_code: string;
  name: string;
  semester: string;
  credits: number;
  grading_scheme?: string;
  start_date: string;
  end_date: string;
  syllabus_text?: string | null;
  is_template?: boolean;
}

export interface CourseCloneRequest {
  template_id: string;
  section_code: string;
  semester: string;
  start_date: string;
  end_date: string;
}

export interface SyllabusUpdate {
  name: string;
  credits: number;
  syllabus_text?: string | null;
}

export interface SyllabusImportTemplateResponse {
  copied_los: number;
  skipped_duplicate_codes: string[];
}

export interface JoinCodeResponse {
  join_code?: string | null;
  is_enrollment_open: boolean;
}

export interface RosterStudentCreate {
  user_code: string;
  full_name: string;
  email: string;
}

export interface RosterItemResponse {
  user_id: string;
  user_code?: string | null;
  full_name: string;
  email: string;
  group_name?: string | null;
  status: EnrollmentStatus;
  enrolled_at: string;
}

export interface RosterPageResponse {
  total: number;
  page: number;
  page_size: number;
  items: RosterItemResponse[];
}

export interface RosterPreviewRow {
  row_number: number;
  user_code: string;
  full_name: string;
  email: string;
  status: RosterRowStatus;
  reason?: string | null;
}

export interface RosterRowError {
  row_number: number;
  reason: string;
}

export interface RosterPreviewResponse {
  total_rows: number;
  valid_count: number;
  duplicate_count: number;
  error_count: number;
  missing_columns: string[];
  preview_rows: RosterPreviewRow[];
  errors: RosterRowError[];
}

export interface RosterImportResult {
  added: number;
  skipped_duplicates: number;
  created_accounts: number;
  errors: RosterRowError[];
}

export interface GroupMemberResponse {
  user_id: string;
  user_code?: string | null;
  full_name: string;
  email: string;
}

export interface GroupItemResponse {
  id?: string | null;
  name: string;
  members: GroupMemberResponse[];
}

export interface GroupSetResponse {
  group_set_name: string;
  groups: GroupItemResponse[];
}

export interface GroupPartitionPreviewRequest {
  group_set_name: string;
  mode: GroupingMode;
  group_size: number;
}

export interface GroupSaveItem {
  name: string;
  member_ids: string[];
}

export interface GroupSetSaveRequest {
  groups: GroupSaveItem[];
}
