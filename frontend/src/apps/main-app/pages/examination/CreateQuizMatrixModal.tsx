/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, Plus, Trash2 } from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type { BloomLevel, LOResponse } from "../../../../types/course";
import type {
  GradeReleasePolicy,
  QuestionBankResponse,
  QuestionResponse,
  QuizDetailResponse,
  SecurityMode,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import {
  BLOOM_OPTIONS,
  fromLocalDateTimeInput,
  GRADE_RELEASE_LABELS,
  SECURITY_MODE_LABELS,
  toLocalDateTimeInput,
} from "./examHelpers";

interface MatrixRowDraft {
  id: string;
  bank_id: string;
  bloom_level: BloomLevel | "";
  lo_id: string;
  count: number;
}

export interface CreateQuizMatrixModalProps {
  open: boolean;
  courseId: string;
  banks: QuestionBankResponse[];
  questions: QuestionResponse[];
  learningObjectives: LOResponse[];
  onClose: () => void;
  onCreated: (quiz: QuizDetailResponse) => void;
}

export const CreateQuizMatrixModal: React.FC<CreateQuizMatrixModalProps> = ({
  open,
  courseId,
  banks,
  questions,
  learningObjectives,
  onClose,
  onCreated,
}) => {
  const [title, setTitle] = useState("");
  const [timeLimitMins, setTimeLimitMins] = useState(45);
  const [availableFrom, setAvailableFrom] = useState("");
  const [availableUntil, setAvailableUntil] = useState("");
  const [securityMode, setSecurityMode] = useState<SecurityMode>("CONTROLLED");
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [gradeReleasePolicy, setGradeReleasePolicy] =
    useState<GradeReleasePolicy>("AFTER_CLOSE");
  const [passcode, setPasscode] = useState("");
  const [ipFilterRange, setIpFilterRange] = useState("");
  const [isAiLocked, setIsAiLocked] = useState(true);
  const [shuffleQuestions, setShuffleQuestions] = useState(true);
  const [shuffleOptions, setShuffleOptions] = useState(true);
  const [rows, setRows] = useState<MatrixRowDraft[]>([]);
  const [loading, setLoading] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const now = new Date();
    const twoHoursLater = new Date(now.getTime() + 2 * 60 * 60 * 1000);
    setTitle("");
    setTimeLimitMins(45);
    setAvailableFrom(toLocalDateTimeInput(now.toISOString()));
    setAvailableUntil(toLocalDateTimeInput(twoHoursLater.toISOString()));
    setSecurityMode("CONTROLLED");
    setMaxAttempts(1);
    setGradeReleasePolicy("AFTER_CLOSE");
    setPasscode("");
    setIpFilterRange("");
    setIsAiLocked(true);
    setShuffleQuestions(true);
    setShuffleOptions(true);
    setRows([
      {
        id: "row-1",
        bank_id: banks[0]?.id ?? "",
        bloom_level: "",
        lo_id: "",
        count: 5,
      },
    ]);
    setBannerError(null);
  }, [open, banks]);

  const countAvailableForRow = (row: MatrixRowDraft): number => {
    if (!row.bank_id) return 0;
    return questions.filter((q) => {
      if (!q.is_active) return false;
      if (q.bank_id !== row.bank_id) return false;
      if (row.bloom_level && q.bloom_level !== row.bloom_level) return false;
      if (row.lo_id && q.lo_id !== row.lo_id) return false;
      return true;
    }).length;
  };

  const totalQuestions = useMemo(
    () => rows.reduce((sum, r) => sum + (Number(r.count) || 0), 0),
    [rows]
  );

  const handleAddRow = () => {
    setRows((prev) => [
      ...prev,
      {
        id: `row-${Date.now()}-${prev.length}`,
        bank_id: banks[0]?.id ?? "",
        bloom_level: "",
        lo_id: "",
        count: 5,
      },
    ]);
  };

  const handleRemoveRow = (id: string) => {
    if (rows.length <= 1) return;
    setRows((prev) => prev.filter((r) => r.id !== id));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBannerError(null);

    if (title.trim().length < 3) {
      setBannerError("Tên kỳ thi phải có ít nhất 3 ký tự.");
      return;
    }

    const fromDate = new Date(availableFrom);
    const untilDate = new Date(availableUntil);
    const diffMins = (untilDate.getTime() - fromDate.getTime()) / 60000;
    if (Number.isNaN(diffMins) || diffMins < timeLimitMins) {
      setBannerError(
        "Khung giờ mở đề thi phải lớn hơn hoặc bằng thời lượng làm bài quy định (E-SEC-01)."
      );
      return;
    }

    if (rows.some((r) => !r.bank_id || r.count < 1)) {
      setBannerError("Vui lòng chọn danh mục và nhập số câu hợp lệ cho từng dòng ma trận.");
      return;
    }

    setLoading(true);
    try {
      const created = await examinationService.createQuiz(courseId, {
        title: title.trim(),
        time_limit_mins: timeLimitMins,
        available_from: fromLocalDateTimeInput(availableFrom),
        available_until: fromLocalDateTimeInput(availableUntil),
        passcode: passcode.trim() || null,
        ip_filter_range: ipFilterRange.trim() || null,
        grade_release_policy: gradeReleasePolicy,
        is_ai_locked: isAiLocked,
        security_mode: securityMode,
        max_attempts: securityMode === "PRACTICE" ? maxAttempts : 1,
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
        snapshot_mode: true,
        matrix_config: rows.map((r) => ({
          bank_id: r.bank_id,
          bloom_level: r.bloom_level || null,
          lo_id: r.lo_id || null,
          count: Number(r.count),
        })),
        question_ids: [],
      });

      showToast(
        "success",
        `Đã tạo đề thi Snapshot "${created.title}" với ${created.question_count} câu hỏi.`
      );
      onCreated(created);
      onClose();
    } catch (err) {
      setBannerError(
        err instanceof ApiError
          ? err.message
          : "Không thể tạo đề thi theo ma trận. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Tạo đề thi theo Ma trận bốc đề Snapshot"
      subtitle="Hệ thống sẽ đóng băng bản chụp câu hỏi bất biến ngay khi tạo đề (BR-EXAM-01)"
      maxWidthClass="max-w-3xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton type="submit" form="create-quiz-form" variant="brand" loading={loading}>
            Tạo đề thi ({totalQuestions} câu)
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

      <form id="create-quiz-form" onSubmit={handleSubmit} noValidate className="space-y-5">
        <FormField label="Tên kỳ thi / Bài kiểm tra" htmlFor="quiz-title" required>
          <input
            id="quiz-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ví dụ: Kiểm tra giữa kỳ - Cấu trúc dữ liệu và Giải thuật"
            className={mmInputClass(false)}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Thời lượng làm bài (phút)" htmlFor="quiz-duration" required>
            <input
              id="quiz-duration"
              type="number"
              min={1}
              max={600}
              value={timeLimitMins}
              onChange={(e) => setTimeLimitMins(Number(e.target.value))}
              className={mmInputClass(false)}
            />
          </FormField>

          <FormField label="Thời điểm mở đề" htmlFor="quiz-from" required>
            <input
              id="quiz-from"
              type="datetime-local"
              value={availableFrom}
              onChange={(e) => setAvailableFrom(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>

          <FormField label="Thời điểm đóng đề" htmlFor="quiz-until" required>
            <input
              id="quiz-until"
              type="datetime-local"
              value={availableUntil}
              onChange={(e) => setAvailableUntil(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Chế độ giám sát an ninh" htmlFor="quiz-sec-mode" required>
            <select
              id="quiz-sec-mode"
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

          <FormField label="Chính sách công bố điểm" htmlFor="quiz-release" required>
            <select
              id="quiz-release"
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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField
            label="Mật khẩu phòng thi (Passcode)"
            htmlFor="quiz-passcode"
            helper="Để trống nếu không yêu cầu mật khẩu"
          >
            <input
              id="quiz-passcode"
              type="text"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              placeholder="vd: LAB2026"
              className={`${mmInputClass(false)} font-mm-mono`}
            />
          </FormField>

          <FormField
            label="Dải IP phòng Lab (CIDR)"
            htmlFor="quiz-cidr"
            helper="Ví dụ: 192.168.10.0/24"
          >
            <input
              id="quiz-cidr"
              type="text"
              value={ipFilterRange}
              onChange={(e) => setIpFilterRange(e.target.value)}
              placeholder="Không giới hạn IP"
              className={`${mmInputClass(false)} font-mm-mono`}
            />
          </FormField>

          <FormField
            label="Số lượt làm bài tối đa"
            htmlFor="quiz-attempts"
            helper={securityMode === "PRACTICE" ? "Chế độ luyện tập cho phép nhiều lượt" : "Chế độ thi chính thức khóa 1 lượt"}
          >
            <input
              id="quiz-attempts"
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

        <div className="flex flex-wrap gap-5 rounded-mm-panel border border-mm-border bg-mm-divider/30 px-4 py-3">
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={shuffleQuestions}
              onChange={(e) => setShuffleQuestions(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Xáo trộn thứ tự câu hỏi</span>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={shuffleOptions}
              onChange={(e) => setShuffleOptions(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Xáo trộn thứ tự đáp án A-B-C-D</span>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 font-mm-ui text-sm text-mm-heading">
            <input
              type="checkbox"
              checked={isAiLocked}
              onChange={(e) => setIsAiLocked(e.target.checked)}
              className="h-4 w-4 accent-mm-blue-hover"
            />
            <span>Khóa Gia sư AI trong giờ thi (E-13)</span>
          </label>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-mm-mid text-base font-medium text-mm-heading">
                Ma trận bốc câu hỏi ngẫu nhiên
              </h3>
              <p className="font-mm-ui text-xs text-mm-text-secondary">
                Tổng số câu sẽ bốc vào Snapshot: {totalQuestions} câu
              </p>
            </div>
            <MmButton variant="secondary" size="sm" onClick={handleAddRow}>
              <Plus className="h-3.5 w-3.5" />
              <span>Thêm dòng ma trận</span>
            </MmButton>
          </div>

          <div className="space-y-2.5">
            {rows.map((row) => {
              const available = countAvailableForRow(row);
              const insufficient = row.count > available;
              return (
                <div
                  key={row.id}
                  className="grid grid-cols-1 gap-2.5 rounded-mm-panel border border-mm-border bg-mm-bg p-3 sm:grid-cols-12 sm:items-center"
                >
                  <div className="sm:col-span-4">
                    <select
                      aria-label="Chọn danh mục câu hỏi"
                      value={row.bank_id}
                      onChange={(e) => {
                        const val = e.target.value;
                        setRows((prev) =>
                          prev.map((r) => (r.id === row.id ? { ...r, bank_id: val } : r))
                        );
                      }}
                      className={mmInputClass(false)}
                    >
                      <option value="">-- Chọn chương --</option>
                      {banks.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.category_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="sm:col-span-3">
                    <select
                      aria-label="Lọc mức Bloom"
                      value={row.bloom_level}
                      onChange={(e) => {
                        const val = e.target.value as BloomLevel | "";
                        setRows((prev) =>
                          prev.map((r) =>
                            r.id === row.id ? { ...r, bloom_level: val } : r
                          )
                        );
                      }}
                      className={mmInputClass(false)}
                    >
                      <option value="">Tất cả mức Bloom</option>
                      {BLOOM_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <select
                      aria-label="Lọc Chuẩn đầu ra"
                      value={row.lo_id}
                      onChange={(e) => {
                        const val = e.target.value;
                        setRows((prev) =>
                          prev.map((r) => (r.id === row.id ? { ...r, lo_id: val } : r))
                        );
                      }}
                      className={mmInputClass(false)}
                    >
                      <option value="">Mọi LO</option>
                      {learningObjectives.map((lo) => (
                        <option key={lo.id} value={lo.id}>
                          {lo.code}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <input
                      type="number"
                      min={1}
                      max={500}
                      aria-label="Số lượng câu hỏi"
                      value={row.count}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setRows((prev) =>
                          prev.map((r) => (r.id === row.id ? { ...r, count: val } : r))
                        );
                      }}
                      className={mmInputClass(insufficient)}
                    />
                    <p
                      className={`mt-0.5 font-mm-data text-[11px] ${
                        insufficient ? "text-mm-danger" : "text-mm-text-muted"
                      }`}
                    >
                      Khả dụng: {available}
                    </p>
                  </div>

                  <div className="flex justify-end sm:col-span-1">
                    {rows.length > 1 && (
                      <button
                        type="button"
                        title="Xóa dòng ma trận"
                        onClick={() => handleRemoveRow(row.id)}
                        className="rounded-mm-tag p-1.5 text-mm-text-muted hover:bg-mm-danger-bg hover:text-mm-danger"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </form>
    </MmModal>
  );
};
