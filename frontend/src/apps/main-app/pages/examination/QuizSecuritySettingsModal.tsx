/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, Copy, RefreshCw } from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type {
  GradeReleasePolicy,
  QuizDetailResponse,
  QuizSummaryResponse,
  SecurityMode,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import {
  fromLocalDateTimeInput,
  GRADE_RELEASE_LABELS,
  SECURITY_MODE_LABELS,
  toLocalDateTimeInput,
} from "./examHelpers";

export interface QuizSecuritySettingsModalProps {
  open: boolean;
  quiz: QuizSummaryResponse | null;
  onClose: () => void;
  onUpdated: (updated: QuizDetailResponse) => void;
}

export const QuizSecuritySettingsModal: React.FC<
  QuizSecuritySettingsModalProps
> = ({ open, quiz, onClose, onUpdated }) => {
  const [title, setTitle] = useState("");
  const [timeLimitMins, setTimeLimitMins] = useState(45);
  const [availableFrom, setAvailableFrom] = useState("");
  const [availableUntil, setAvailableUntil] = useState("");
  const [passcode, setPasscode] = useState("");
  const [ipFilterRange, setIpFilterRange] = useState("");
  const [securityMode, setSecurityMode] = useState<SecurityMode>("CONTROLLED");
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [gradeReleasePolicy, setGradeReleasePolicy] =
    useState<GradeReleasePolicy>("AFTER_CLOSE");
  const [isAiLocked, setIsAiLocked] = useState(true);
  const [shuffleQuestions, setShuffleQuestions] = useState(true);
  const [shuffleOptions, setShuffleOptions] = useState(true);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !quiz) return;
    setTitle(quiz.title);
    setTimeLimitMins(quiz.time_limit_mins);
    setAvailableFrom(toLocalDateTimeInput(quiz.available_from));
    setAvailableUntil(toLocalDateTimeInput(quiz.available_until));
    setPasscode(quiz.passcode ?? "");
    setIpFilterRange(quiz.ip_filter_range ?? "");
    setSecurityMode(quiz.security_mode);
    setMaxAttempts(quiz.max_attempts);
    setGradeReleasePolicy(quiz.grade_release_policy);
    setIsAiLocked(quiz.is_ai_locked);
    setShuffleQuestions(quiz.shuffle_questions);
    setShuffleOptions(quiz.shuffle_options);
    setBannerError(null);
  }, [open, quiz]);

  const handleRegeneratePasscode = async () => {
    if (!quiz) return;
    setRegenerating(true);
    try {
      const res = await examinationService.regeneratePasscode(quiz.id);
      setPasscode(res.passcode);
      showToast(
        "success",
        `Đã đổi mật khẩu phòng thi khẩn cấp thành: ${res.passcode}`
      );
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError
          ? err.message
          : "Không thể đổi mật khẩu phòng thi khẩn cấp."
      );
    } finally {
      setRegenerating(false);
    }
  };

  const handleCopyPasscode = async () => {
    if (!passcode.trim()) return;
    try {
      await navigator.clipboard.writeText(passcode.trim());
      showToast("success", "Đã sao chép mật khẩu phòng thi.");
    } catch {
      showToast("error", "Trình duyệt không cho phép sao chép tự động.");
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!quiz) return;
    setBannerError(null);

    const fromDate = new Date(availableFrom);
    const untilDate = new Date(availableUntil);
    const diffMins = (untilDate.getTime() - fromDate.getTime()) / 60000;
    if (Number.isNaN(diffMins) || diffMins < timeLimitMins) {
      setBannerError(
        "Khung giờ mở đề thi phải lớn hơn hoặc bằng thời lượng làm bài quy định (E-SEC-01)."
      );
      return;
    }

    setLoading(true);
    try {
      const updated = await examinationService.updateQuizSettings(quiz.id, {
        title: title.trim() || quiz.title,
        time_limit_mins: timeLimitMins,
        available_from: fromLocalDateTimeInput(availableFrom),
        available_until: fromLocalDateTimeInput(availableUntil),
        passcode: passcode.trim() || null,
        ip_filter_range: ipFilterRange.trim() || null,
        security_mode: securityMode,
        max_attempts: securityMode === "PRACTICE" ? maxAttempts : 1,
        grade_release_policy: gradeReleasePolicy,
        is_ai_locked: isAiLocked,
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
      });

      showToast("success", "Đã lưu cấu hình phòng thi và an ninh.");
      onUpdated(updated);
      onClose();
    } catch (err) {
      setBannerError(
        err instanceof ApiError
          ? err.message
          : "Không thể cập nhật cấu hình phòng thi."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Cấu hình phòng thi & An ninh"
      subtitle={quiz ? quiz.title : undefined}
      maxWidthClass="max-w-2xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton
            type="submit"
            form="quiz-settings-form"
            variant="brand"
            loading={loading}
          >
            Lưu cấu hình
          </MmButton>
        </>
      }
    >
      {bannerError && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{bannerError}</span>
        </div>
      )}

      <form
        id="quiz-settings-form"
        onSubmit={handleSubmit}
        noValidate
        className="space-y-4"
      >
        <FormField label="Tên kỳ thi" htmlFor="set-title" required>
          <input
            id="set-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={mmInputClass(false)}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Thời lượng (phút)" htmlFor="set-duration" required>
            <input
              id="set-duration"
              type="number"
              min={1}
              max={600}
              value={timeLimitMins}
              onChange={(e) => setTimeLimitMins(Number(e.target.value))}
              className={mmInputClass(false)}
            />
          </FormField>

          <FormField label="Mở đề từ" htmlFor="set-from" required>
            <input
              id="set-from"
              type="datetime-local"
              value={availableFrom}
              onChange={(e) => setAvailableFrom(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>

          <FormField label="Đóng đề lúc" htmlFor="set-until" required>
            <input
              id="set-until"
              type="datetime-local"
              value={availableUntil}
              onChange={(e) => setAvailableUntil(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>
        </div>

        <div className="rounded-mm-panel border border-mm-border bg-mm-divider/30 p-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="font-mm-ui text-sm font-medium text-mm-heading">
              Mật khẩu phòng thi (Passcode)
            </span>
            <div className="flex items-center gap-2">
              {passcode && (
                <MmButton
                  variant="secondary"
                  size="sm"
                  onClick={handleCopyPasscode}
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>Sao chép</span>
                </MmButton>
              )}
              <MmButton
                variant="danger"
                size="sm"
                loading={regenerating}
                onClick={handleRegeneratePasscode}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Đổi Passcode khẩn cấp</span>
              </MmButton>
            </div>
          </div>
          <input
            type="text"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder="Để trống nếu không yêu cầu mật khẩu"
            className={`${mmInputClass(false)} font-mm-mono`}
          />
          <p className="mt-1.5 font-mm-ui text-xs text-mm-text-helper">
            Khi bấm Đổi Passcode khẩn cấp, mã mới 6 ký tự sẽ có hiệu lực ngay với các thí sinh chưa vào phòng thi.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Dải IP phòng Lab (CIDR)"
            htmlFor="set-cidr"
            helper="Ví dụ: 10.20.0.0/16 hoặc để trống"
          >
            <input
              id="set-cidr"
              type="text"
              value={ipFilterRange}
              onChange={(e) => setIpFilterRange(e.target.value)}
              placeholder="Không giới hạn IP"
              className={`${mmInputClass(false)} font-mm-mono`}
            />
          </FormField>

          <FormField label="Số lượt làm bài tối đa" htmlFor="set-attempts">
            <input
              id="set-attempts"
              type="number"
              min={1}
              max={100}
              disabled={securityMode !== "PRACTICE"}
              value={securityMode === "PRACTICE" ? maxAttempts : 1}
              onChange={(e) => setMaxAttempts(Number(e.target.value))}
              className={mmInputClass(false)}
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Chế độ giám sát" htmlFor="set-sec" required>
            <select
              id="set-sec"
              value={securityMode}
              onChange={(e) => {
                const mode = e.target.value as SecurityMode;
                setSecurityMode(mode);
                if (mode !== "PRACTICE") setMaxAttempts(1);
              }}
              className={mmInputClass(false)}
            >
              {(Object.keys(SECURITY_MODE_LABELS) as SecurityMode[]).map((mode) => (
                <option key={mode} value={mode}>
                  {SECURITY_MODE_LABELS[mode]}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Chính sách công bố điểm" htmlFor="set-policy" required>
            <select
              id="set-policy"
              value={gradeReleasePolicy}
              onChange={(e) =>
                setGradeReleasePolicy(e.target.value as GradeReleasePolicy)
              }
              className={mmInputClass(false)}
            >
              {(Object.keys(GRADE_RELEASE_LABELS) as GradeReleasePolicy[]).map(
                (policy) => (
                  <option key={policy} value={policy}>
                    {GRADE_RELEASE_LABELS[policy]}
                  </option>
                )
              )}
            </select>
          </FormField>
        </div>

        <div className="flex flex-wrap gap-5 pt-1">
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={shuffleQuestions}
              onChange={(e) => setShuffleQuestions(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Xáo trộn câu hỏi</span>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={shuffleOptions}
              onChange={(e) => setShuffleOptions(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Xáo trộn đáp án</span>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={isAiLocked}
              onChange={(e) => setIsAiLocked(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Khóa Gia sư AI (E-13)</span>
          </label>
        </div>
      </form>
    </MmModal>
  );
};
