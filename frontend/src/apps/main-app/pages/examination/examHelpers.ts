/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type { BloomLevel } from "../../../../types/course";
import type {
  DecimalValue,
  GradeReleasePolicy,
  QuestionType,
  QuizStatus,
  RegradeScope,
  RegradeStatus,
  SecurityMode,
} from "../../../../types/examination";

export const BLOOM_OPTIONS: Array<{ value: BloomLevel; label: string }> = [
  { value: "REMEMBER", label: "Nhận biết (Remember)" },
  { value: "UNDERSTAND", label: "Thông hiểu (Understand)" },
  { value: "APPLY", label: "Vận dụng (Apply)" },
  { value: "ANALYZE", label: "Phân tích (Analyze)" },
  { value: "EVALUATE", label: "Đánh giá (Evaluate)" },
  { value: "CREATE", label: "Sáng tạo (Create)" },
];

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  MULTIPLE_CHOICE: "Trắc nghiệm 1 đáp án",
  MULTI_SELECT: "Chọn nhiều đáp án",
};

export const QUIZ_STATUS_META: Record<
  QuizStatus,
  { label: string; className: string }
> = {
  DRAFT: {
    label: "Bản nháp",
    className: "bg-mm-btn-secondary text-mm-text-secondary",
  },
  PUBLISHED: {
    label: "Đã xuất bản",
    className: "bg-mm-success-bg text-mm-success",
  },
  CLOSED: {
    label: "Đã đóng",
    className: "bg-mm-divider text-mm-text-muted",
  },
};

export const SECURITY_MODE_LABELS: Record<SecurityMode, string> = {
  CONTROLLED: "Phòng thi giám sát chặt (Controlled)",
  REMOTE_PROCTORED: "Thi từ xa có giám sát (Remote Proctored)",
  PRACTICE: "Luyện tập (Practice)",
};

export const GRADE_RELEASE_LABELS: Record<GradeReleasePolicy, string> = {
  IMMEDIATE: "Công bố ngay sau khi nộp bài",
  AFTER_CLOSE: "Tự động mở sau giờ đóng đề",
  MANUAL: "Chờ Giảng viên bấm Công bố điểm",
};

export const REGRADE_STATUS_META: Record<
  RegradeStatus,
  { label: string; className: string }
> = {
  PENDING: {
    label: "Chờ duyệt",
    className: "bg-mm-warning-bg text-mm-warning",
  },
  APPROVED: {
    label: "Đã chấp thuận",
    className: "bg-mm-success-bg text-mm-success",
  },
  REJECTED: {
    label: "Đã từ chối",
    className: "bg-mm-danger-bg text-mm-danger",
  },
};

export const REGRADE_SCOPE_LABELS: Record<RegradeScope, string> = {
  SINGLE_STUDENT: "Cá nhân sinh viên",
  ENTIRE_CLASS: "Chấm lại toàn lớp",
};

export function toNumeric(value: DecimalValue | null | undefined, fallback = 0): number {
  if (value === null || value === undefined) return fallback;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function formatScore(value: DecimalValue | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return toNumeric(value).toFixed(1);
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function toLocalDateTimeInput(iso?: string | null): string {
  const date = iso ? new Date(iso) : new Date();
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fromLocalDateTimeInput(localStr: string): string {
  const date = new Date(localStr);
  return date.toISOString();
}

export function formatCountdown(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(clamped / 3600);
  const mins = Math.floor((clamped % 3600) / 60);
  const secs = clamped % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  if (hours > 0) {
    return `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
  }
  return `${pad(mins)}:${pad(secs)}`;
}

export function getDraftStorageKey(submissionId: string): string {
  return `adlas_exam_draft_${submissionId}`;
}

export function getLastSubmissionStorageKey(quizId: string): string {
  return `adlas_exam_last_submission_${quizId}`;
}
