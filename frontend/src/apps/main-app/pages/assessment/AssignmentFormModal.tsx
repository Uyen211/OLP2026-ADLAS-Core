/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  FileUp,
  Paperclip,
  Send,
  Save,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
  Sparkles,
  Trash2,
} from "lucide-react";
import { RichTextEditor } from "../../../../components/editors/RichTextEditor";
import { assessmentService } from "../../../../services/assessmentService";
import { ApiError } from "../../../../services/httpClient";
import type {
  AIPolicyLevel,
  AssignmentAuthoringResponse,
  AssignmentCreateRequest,
  AssignmentDetail,
  AssignmentUpdateRequest,
  SubmissionType,
} from "../../../../types/assessment";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface AssignmentFormModalProps {
  open: boolean;
  courseId: string;
  editingAssignment?: AssignmentDetail | AssignmentAuthoringResponse | null;
  onClose: () => void;
  onSaved: (saved: AssignmentAuthoringResponse) => void;
}

const SUBMISSION_TYPE_OPTIONS: Array<{ value: SubmissionType; label: string }> = [
  { value: "FILE_UPLOAD", label: "Tải tệp lên hệ thống" },
  { value: "GIT_REPOSITORY", label: "Nộp liên kết kho mã nguồn Git" },
  { value: "HYBRID", label: "Kết hợp Tải tệp và Kho mã nguồn Git" },
];

const LATE_PENALTY_PRESETS = [0, 5, 10, 20];

const AI_POLICY_OPTIONS: Array<{
  level: AIPolicyLevel;
  title: string;
  badge: string;
  description: string;
  activeClass: string;
  badgeClass: string;
  icon: "green" | "yellow" | "red";
}> = [
  {
    level: "GREEN",
    title: "Mức Xanh — Cho phép AI hỗ trợ",
    badge: "Xanh",
    description:
      "Sinh viên được dùng công cụ AI hỗ trợ tra cứu, gợi ý ý tưởng và cần khai báo minh bạch.",
    activeClass: "border-mm-success bg-mm-success-bg/60",
    badgeClass: "bg-mm-success-bg text-mm-success",
    icon: "green",
  },
  {
    level: "YELLOW",
    title: "Mức Vàng — Giới hạn có kiểm soát",
    badge: "Vàng",
    description:
      "Chỉ được dùng AI ở các công đoạn cho phép; bắt buộc ký cam kết liêm chính và giải trình chi tiết.",
    activeClass: "border-mm-warning bg-mm-warning-bg/60",
    badgeClass: "bg-mm-warning-bg text-mm-warning",
    icon: "yellow",
  },
  {
    level: "RED",
    title: "Mức Đỏ — Cấm sử dụng AI",
    badge: "Đỏ",
    description:
      "Yêu cầu 100% sinh viên tự thực hiện, không sử dụng AI sinh mã hoặc viết nội dung; bắt buộc ký cam kết.",
    activeClass: "border-mm-danger bg-mm-danger-bg/60",
    badgeClass: "bg-mm-danger-bg text-mm-danger",
    icon: "red",
  },
];

function toLocalDatetimeInput(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

function defaultDueDateInput(): string {
  const target = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  target.setHours(23, 59, 0, 0);
  return toLocalDatetimeInput(target.toISOString());
}

function toIsoOrNull(localValue: string): string | null {
  if (!localValue.trim()) return null;
  const date = new Date(localValue);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function stripHtmlText(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export const AssignmentFormModal: React.FC<AssignmentFormModalProps> = ({
  open,
  courseId,
  editingAssignment,
  onClose,
  onSaved,
}) => {
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");
  const [uploadingAttachment, setUploadingAttachment] = useState(false);

  const [submissionType, setSubmissionType] = useState<SubmissionType>("FILE_UPLOAD");
  const [allowedExtensions, setAllowedExtensions] = useState(".zip,.pdf,.docx");
  const [maxFileSizeMb, setMaxFileSizeMb] = useState(50);
  const [isGroupAssignment, setIsGroupAssignment] = useState(false);
  const [isTransferTask, setIsTransferTask] = useState(false);
  const [maxAttempts, setMaxAttempts] = useState("");

  const [availableFrom, setAvailableFrom] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [untilDate, setUntilDate] = useState("");
  const [latePenaltyPercent, setLatePenaltyPercent] = useState(5);

  const [aiPolicyLevel, setAiPolicyLevel] = useState<AIPolicyLevel>("YELLOW");
  const [isVivaRequired, setIsVivaRequired] = useState(true);
  const [vivaQuestionCount, setVivaQuestionCount] = useState(3);

  const [savingMode, setSavingMode] = useState<"draft" | "publish" | null>(null);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [instructionsError, setInstructionsError] = useState<string | null>(null);
  const [dueDateError, setDueDateError] = useState<string | null>(null);
  const [maxAttemptsError, setMaxAttemptsError] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingAssignment) {
      setTitle(editingAssignment.title);
      setInstructions(editingAssignment.instructions || "");
      setAttachmentUrl(editingAssignment.attachment_url ?? "");
      setSubmissionType(
        (editingAssignment.submission_type as SubmissionType) || "FILE_UPLOAD"
      );
      setAllowedExtensions(editingAssignment.allowed_extensions || ".zip,.pdf,.docx");
      setMaxFileSizeMb(editingAssignment.max_file_size_mb || 50);
      setIsGroupAssignment(Boolean(editingAssignment.is_group_assignment));
      setIsTransferTask(Boolean(editingAssignment.is_transfer_task));
      setMaxAttempts(
        editingAssignment.max_attempts !== null &&
          editingAssignment.max_attempts !== undefined
          ? String(editingAssignment.max_attempts)
          : ""
      );
      setAvailableFrom(toLocalDatetimeInput(editingAssignment.available_from));
      setDueDate(toLocalDatetimeInput(editingAssignment.due_date));
      setUntilDate(toLocalDatetimeInput(editingAssignment.until_date));
      setLatePenaltyPercent(Number(editingAssignment.late_penalty_percent ?? 5));
      setAiPolicyLevel(
        (editingAssignment.ai_policy_level as AIPolicyLevel) || "YELLOW"
      );
      setIsVivaRequired(Boolean(editingAssignment.is_viva_required));
      setVivaQuestionCount(editingAssignment.viva_question_count || 3);
    } else {
      setTitle("");
      setInstructions("");
      setAttachmentUrl("");
      setSubmissionType("FILE_UPLOAD");
      setAllowedExtensions(".zip,.pdf,.docx");
      setMaxFileSizeMb(50);
      setIsGroupAssignment(false);
      setIsTransferTask(false);
      setMaxAttempts("");
      setAvailableFrom("");
      setDueDate(defaultDueDateInput());
      setUntilDate("");
      setLatePenaltyPercent(5);
      setAiPolicyLevel("YELLOW");
      setIsVivaRequired(true);
      setVivaQuestionCount(3);
    }
    setTitleError(null);
    setInstructionsError(null);
    setDueDateError(null);
    setMaxAttemptsError(null);
    setBannerError(null);
    setSavingMode(null);
  }, [open, editingAssignment]);

  // Kiểm tra tức thì ràng buộc lịch nộp bài E-ASN-01: available_from <= due_date <= until_date
  const scheduleValidation = useMemo(() => {
    const availMs = availableFrom ? new Date(availableFrom).getTime() : null;
    const dueMs = dueDate ? new Date(dueDate).getTime() : null;
    const untilMs = untilDate ? new Date(untilDate).getTime() : null;

    let availableError: string | null = null;
    let untilError: string | null = null;

    if (
      availMs !== null &&
      dueMs !== null &&
      !Number.isNaN(availMs) &&
      !Number.isNaN(dueMs) &&
      dueMs < availMs
    ) {
      availableError =
        "E-ASN-01: Thời điểm mở nhận bài không được lớn hơn Hạn nộp chính thức (Due Date).";
    }

    if (
      dueMs !== null &&
      untilMs !== null &&
      !Number.isNaN(dueMs) &&
      !Number.isNaN(untilMs) &&
      untilMs < dueMs
    ) {
      untilError =
        "E-ASN-01: Hạn đóng cổng nộp trễ (Until Date) phải lớn hơn hoặc bằng Hạn nộp chính thức (Due Date).";
    }

    return {
      availableError,
      untilError,
      hasError: Boolean(availableError || untilError),
    };
  }, [availableFrom, dueDate, untilDate]);

  const handleAttachmentUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadingAttachment(true);
    setBannerError(null);
    try {
      const uploaded = await assessmentService.uploadFile(file);
      setAttachmentUrl(uploaded.file_url);
      showToast("success", `Đã tải tệp đề bài "${uploaded.file_name}" lên hệ thống.`);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải tệp đính kèm đề bài."
      );
    } finally {
      setUploadingAttachment(false);
      event.target.value = "";
    }
  };

  const validateFields = (): boolean => {
    let valid = true;
    const cleanedTitle = title.trim();

    if (cleanedTitle.length < 5 || cleanedTitle.length > 150) {
      setTitleError("Tiêu đề bài tập phải có độ dài từ 5 đến 150 ký tự.");
      valid = false;
    } else {
      setTitleError(null);
    }

    if (stripHtmlText(instructions).length === 0) {
      setInstructionsError("Vui lòng nhập nội dung đề bài hoặc hướng dẫn thực hiện.");
      valid = false;
    } else {
      setInstructionsError(null);
    }

    if (!dueDate || Number.isNaN(new Date(dueDate).getTime())) {
      setDueDateError("Vui lòng chọn Hạn nộp chính thức (Due Date).");
      valid = false;
    } else {
      setDueDateError(null);
    }

    if (maxAttempts.trim() !== "") {
      const parsed = Number(maxAttempts);
      if (!Number.isInteger(parsed) || parsed < 1 || parsed > 50) {
        setMaxAttemptsError("Số lần nộp tối đa phải là số nguyên từ 1 đến 50.");
        valid = false;
      } else {
        setMaxAttemptsError(null);
      }
    } else {
      setMaxAttemptsError(null);
    }

    if (scheduleValidation.hasError) {
      valid = false;
    }

    return valid;
  };

  const handleSave = async (shouldPublish: boolean) => {
    if (!validateFields()) return;

    const dueIso = toIsoOrNull(dueDate);
    if (!dueIso) {
      setDueDateError("Định dạng Hạn nộp chính thức không hợp lệ.");
      return;
    }

    const parsedAttempts =
      maxAttempts.trim() !== "" ? Number(maxAttempts.trim()) : null;
    const clampedSize = Math.min(500, Math.max(1, Number(maxFileSizeMb) || 50));
    const clampedPenalty = Math.min(100, Math.max(0, Number(latePenaltyPercent) || 0));
    const clampedViva = Math.min(10, Math.max(1, Number(vivaQuestionCount) || 3));

    setSavingMode(shouldPublish ? "publish" : "draft");
    setBannerError(null);

    try {
      let saved: AssignmentAuthoringResponse;

      if (editingAssignment) {
        const updatePayload: AssignmentUpdateRequest = {
          title: title.trim(),
          instructions,
          attachment_url: attachmentUrl.trim() || null,
          submission_type: submissionType,
          allowed_extensions: allowedExtensions.trim() || ".zip,.pdf,.docx",
          max_file_size_mb: clampedSize,
          is_group_assignment: isGroupAssignment,
          is_transfer_task: isTransferTask,
          available_from: toIsoOrNull(availableFrom),
          due_date: dueIso,
          until_date: toIsoOrNull(untilDate),
          late_penalty_percent: clampedPenalty,
          is_viva_required: isVivaRequired,
          viva_question_count: clampedViva,
          ai_policy_level: aiPolicyLevel,
          max_attempts: parsedAttempts,
        };
        saved = await assessmentService.updateAssignment(
          editingAssignment.id,
          updatePayload
        );
        if (shouldPublish && !saved.is_published) {
          saved = await assessmentService.publishAssignment(saved.id);
        }
        showToast(
          "success",
          shouldPublish && editingAssignment.is_published === false
            ? "Đã lưu và xuất bản bài tập cho sinh viên."
            : "Đã cập nhật cấu hình bài tập thành công."
        );
      } else {
        const createPayload: AssignmentCreateRequest = {
          title: title.trim(),
          instructions,
          attachment_url: attachmentUrl.trim() || null,
          submission_type: submissionType,
          allowed_extensions: allowedExtensions.trim() || ".zip,.pdf,.docx",
          max_file_size_mb: clampedSize,
          is_group_assignment: isGroupAssignment,
          is_transfer_task: isTransferTask,
          available_from: toIsoOrNull(availableFrom),
          due_date: dueIso,
          until_date: toIsoOrNull(untilDate),
          late_penalty_percent: clampedPenalty,
          is_viva_required: isVivaRequired,
          viva_question_count: clampedViva,
          ai_policy_level: aiPolicyLevel,
          max_attempts: parsedAttempts,
          publish: shouldPublish,
        };
        saved = await assessmentService.createAssignment(courseId, createPayload);
        showToast(
          "success",
          shouldPublish
            ? "Đã tạo và xuất bản bài tập thành công."
            : "Đã lưu bài tập ở trạng thái bản nháp."
        );
      }

      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setBannerError(err.message);
      } else {
        setBannerError("Không thể lưu cấu hình bài tập. Vui lòng thử lại.");
      }
    } finally {
      setSavingMode(null);
    }
  };

  const isBusy = savingMode !== null || uploadingAttachment;
  const isAlreadyPublished = Boolean(
    editingAssignment && editingAssignment.is_published !== false
  );

  return (
    <MmModal
      open={open}
      title={
        editingAssignment
          ? "Chỉnh sửa cấu hình bài tập / đồ án"
          : "Tạo bài tập / đồ án mới"
      }
      subtitle="Thiết lập đề bài, lịch hạn chót (Due Date / Until Date), chính sách AI và vấn đáp Viva Sandbox"
      maxWidthClass="max-w-3xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={isBusy}>
            Hủy bỏ
          </MmButton>

          {!isAlreadyPublished && (
            <MmButton
              variant="secondary"
              loading={savingMode === "draft"}
              disabled={isBusy || scheduleValidation.hasError}
              onClick={() => void handleSave(false)}
            >
              <Save className="h-4 w-4" />
              <span>Lưu bản nháp</span>
            </MmButton>
          )}

          <MmButton
            variant="brand"
            loading={savingMode === "publish"}
            disabled={isBusy || scheduleValidation.hasError}
            onClick={() => void handleSave(true)}
          >
            <Send className="h-4 w-4" />
            <span>
              {isAlreadyPublished ? "Lưu thay đổi" : "Lưu & Xuất bản"}
            </span>
          </MmButton>
        </>
      }
    >
      <div className="space-y-6">
        {bannerError && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="font-mm-ui text-sm">{bannerError}</span>
          </div>
        )}

        {/* Phần 1: Thông tin chung & Đề bài */}
        <section className="space-y-4">
          <div className="border-b border-mm-divider pb-2">
            <h3 className="font-mm-display text-base font-semibold text-mm-heading">
              Thông tin chung &amp; Đề bài
            </h3>
          </div>

          <FormField
            label="Tiêu đề bài tập / đồ án"
            htmlFor="assignment-title"
            required
            error={titleError}
            helper={`Độ dài yêu cầu: 5 - 150 ký tự (hiện tại ${title.trim().length}/150)`}
          >
            <input
              id="assignment-title"
              type="text"
              maxLength={150}
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (titleError) setTitleError(null);
              }}
              placeholder="Ví dụ: Đồ án giữa kỳ — Xây dựng dịch vụ quản lý thư viện"
              className={mmInputClass(Boolean(titleError))}
            />
          </FormField>

          <FormField
            label="Nội dung đề bài & Hướng dẫn thực hiện"
            required
            error={instructionsError}
          >
            <RichTextEditor
              value={instructions}
              onChange={(html) => {
                setInstructions(html);
                if (instructionsError) setInstructionsError(null);
              }}
            />
          </FormField>

          <FormField
            label="Tệp đính kèm đề bài (tùy chọn)"
            htmlFor="assignment-attachment-url"
            helper="Tải tệp đặc tả/mẫu bài làm lên máy chủ hoặc dán đường dẫn tài liệu"
          >
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative flex-1">
                <Paperclip className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mm-text-muted" />
                <input
                  id="assignment-attachment-url"
                  type="text"
                  maxLength={500}
                  value={attachmentUrl}
                  onChange={(e) => setAttachmentUrl(e.target.value)}
                  placeholder="https://... hoặc tải tệp từ máy"
                  className={clsx(mmInputClass(false), "pl-9")}
                />
              </div>
              <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-mm-btn bg-mm-btn-secondary px-4 py-2.5 font-mm-ui text-sm font-semibold text-mm-heading transition-colors hover:bg-mm-border">
                <FileUp className="h-4 w-4" />
                <span>{uploadingAttachment ? "Đang tải..." : "Tải tệp lên"}</span>
                <input
                  type="file"
                  className="hidden"
                  disabled={uploadingAttachment}
                  onChange={(e) => void handleAttachmentUpload(e)}
                />
              </label>
              {attachmentUrl && (
                <button
                  type="button"
                  title="Xóa tệp đính kèm"
                  onClick={() => setAttachmentUrl("")}
                  className="inline-flex items-center justify-center rounded-mm-btn border border-mm-border px-3 py-2 text-mm-danger transition-colors hover:bg-mm-danger-bg"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </FormField>
        </section>

        {/* Phần 2: Hình thức nộp & Giới hạn tệp */}
        <section className="space-y-4">
          <div className="border-b border-mm-divider pb-2">
            <h3 className="font-mm-display text-base font-semibold text-mm-heading">
              Hình thức nộp bài &amp; Quy định tệp
            </h3>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Phương thức nộp bài" htmlFor="assignment-sub-type">
              <select
                id="assignment-sub-type"
                value={submissionType}
                onChange={(e) => setSubmissionType(e.target.value as SubmissionType)}
                className={mmInputClass(false)}
              >
                {SUBMISSION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField
              label="Số lần nộp tối đa (tùy chọn)"
              htmlFor="assignment-max-attempts"
              error={maxAttemptsError}
              helper="Để trống nếu cho phép nộp nhiều phiên bản"
            >
              <input
                id="assignment-max-attempts"
                type="number"
                min={1}
                max={50}
                value={maxAttempts}
                onChange={(e) => {
                  setMaxAttempts(e.target.value);
                  if (maxAttemptsError) setMaxAttemptsError(null);
                }}
                placeholder="Không giới hạn"
                className={mmInputClass(Boolean(maxAttemptsError))}
              />
            </FormField>

            <FormField
              label="Định dạng tệp cho phép"
              htmlFor="assignment-extensions"
              helper="Phân tách bằng dấu phẩy, ví dụ: .zip,.pdf,.docx"
            >
              <input
                id="assignment-extensions"
                type="text"
                maxLength={100}
                value={allowedExtensions}
                onChange={(e) => setAllowedExtensions(e.target.value)}
                className={mmInputClass(false)}
              />
            </FormField>

            <FormField
              label="Dung lượng tối đa (MB)"
              htmlFor="assignment-max-size"
              helper="Từ 1 MB đến 500 MB"
            >
              <input
                id="assignment-max-size"
                type="number"
                min={1}
                max={500}
                value={maxFileSizeMb}
                onChange={(e) => setMaxFileSizeMb(Number(e.target.value))}
                className={mmInputClass(false)}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="flex cursor-pointer items-start gap-3 rounded-mm-panel border border-mm-border bg-mm-bg p-3.5 transition-colors hover:border-mm-blue-hover">
              <input
                type="checkbox"
                checked={isGroupAssignment}
                onChange={(e) => setIsGroupAssignment(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
              />
              <div>
                <span className="block font-mm-ui text-sm font-medium text-mm-heading">
                  Bài tập thực hiện theo nhóm
                </span>
                <span className="block font-mm-ui text-xs text-mm-text-secondary">
                  Một thành viên đại diện nộp bài cho cả nhóm học phần
                </span>
              </div>
            </label>

            <label className="flex cursor-pointer items-start gap-3 rounded-mm-panel border border-mm-border bg-mm-bg p-3.5 transition-colors hover:border-mm-blue-hover">
              <input
                type="checkbox"
                checked={isTransferTask}
                onChange={(e) => setIsTransferTask(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
              />
              <div>
                <span className="block font-mm-ui text-sm font-medium text-mm-heading">
                  Nhiệm vụ chuyển giao năng lực (Transfer Task)
                </span>
                <span className="block font-mm-ui text-xs text-mm-text-secondary">
                  Đánh dấu bài tập tổng hợp dùng cho hồ sơ năng lực đầu ra
                </span>
              </div>
            </label>
          </div>
        </section>

        {/* Phần 3: Lịch nộp bài & Phạt nộp trễ */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 border-b border-mm-divider pb-2">
            <CalendarClock className="h-4 w-4 text-mm-blue-hover" />
            <h3 className="font-mm-display text-base font-semibold text-mm-heading">
              Lịch mở đề, Hạn nộp (Due Date) &amp; Hạn khóa cổng (Until Date)
            </h3>
          </div>

          {scheduleValidation.hasError && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="space-y-1 font-mm-ui text-xs">
                {scheduleValidation.availableError && (
                  <p>{scheduleValidation.availableError}</p>
                )}
                {scheduleValidation.untilError && (
                  <p>{scheduleValidation.untilError}</p>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Thời điểm mở nhận bài"
              htmlFor="assignment-available-from"
              error={scheduleValidation.availableError}
              helper="Để trống để mở ngay khi xuất bản"
            >
              <input
                id="assignment-available-from"
                type="datetime-local"
                value={availableFrom}
                onChange={(e) => setAvailableFrom(e.target.value)}
                className={mmInputClass(Boolean(scheduleValidation.availableError))}
              />
            </FormField>

            <FormField
              label="Hạn nộp chính thức (Due Date)"
              htmlFor="assignment-due-date"
              required
              error={dueDateError}
              helper="Nộp sau mốc này bị tính nộp trễ"
            >
              <input
                id="assignment-due-date"
                type="datetime-local"
                value={dueDate}
                onChange={(e) => {
                  setDueDate(e.target.value);
                  if (dueDateError) setDueDateError(null);
                }}
                className={mmInputClass(
                  Boolean(dueDateError || scheduleValidation.availableError)
                )}
              />
            </FormField>

            <FormField
              label="Hạn đóng cổng (Until Date)"
              htmlFor="assignment-until-date"
              error={scheduleValidation.untilError}
              helper="Phải lớn hơn hoặc bằng Due Date"
            >
              <input
                id="assignment-until-date"
                type="datetime-local"
                value={untilDate}
                onChange={(e) => setUntilDate(e.target.value)}
                className={mmInputClass(Boolean(scheduleValidation.untilError))}
              />
            </FormField>
          </div>

          <FormField
            label="Tỷ lệ trừ điểm khi nộp trễ (% / ngày)"
            htmlFor="assignment-late-penalty"
            helper="Chọn nhanh mức phổ biến hoặc nhập tỷ lệ tùy chỉnh từ 0% đến 100%"
          >
            <div className="flex flex-wrap items-center gap-2">
              {LATE_PENALTY_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setLatePenaltyPercent(preset)}
                  className={clsx(
                    "rounded-mm-btn border px-3.5 py-2 font-mm-data text-xs font-semibold transition-colors",
                    latePenaltyPercent === preset
                      ? "border-mm-blue-hover bg-mm-blue-light/35 text-mm-blue-deep"
                      : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/50"
                  )}
                >
                  {preset}%
                </button>
              ))}
              <div className="w-28">
                <input
                  id="assignment-late-penalty"
                  type="number"
                  min={0}
                  max={100}
                  step="0.5"
                  value={latePenaltyPercent}
                  onChange={(e) => setLatePenaltyPercent(Number(e.target.value))}
                  className={mmInputClass(false)}
                />
              </div>
            </div>
          </FormField>
        </section>

        {/* Phần 4: Chính sách AI & Vấn đáp Viva Sandbox */}
        <section className="space-y-4">
          <div className="border-b border-mm-divider pb-2">
            <h3 className="font-mm-display text-base font-semibold text-mm-heading">
              Chính sách sử dụng AI &amp; Vấn đáp Viva Sandbox
            </h3>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {AI_POLICY_OPTIONS.map((opt) => {
              const selected = aiPolicyLevel === opt.level;
              const Icon =
                opt.icon === "green"
                  ? ShieldCheck
                  : opt.icon === "yellow"
                    ? ShieldAlert
                    : ShieldOff;

              return (
                <button
                  key={opt.level}
                  type="button"
                  onClick={() => setAiPolicyLevel(opt.level)}
                  className={clsx(
                    "flex flex-col items-start gap-2 rounded-mm-card border p-4 text-left transition-all",
                    selected
                      ? opt.activeClass
                      : "border-mm-border bg-mm-bg hover:border-mm-text-muted"
                  )}
                >
                  <div className="flex w-full items-center justify-between">
                    <span
                      className={clsx(
                        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mm-ui text-xs font-medium",
                        opt.badgeClass
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span>{opt.badge}</span>
                    </span>
                    {selected && (
                      <CheckCircle2 className="h-4 w-4 text-mm-heading" />
                    )}
                  </div>
                  <span className="font-mm-mid text-sm font-medium text-mm-heading">
                    {opt.title}
                  </span>
                  <span className="font-mm-ui text-xs leading-relaxed text-mm-text-secondary">
                    {opt.description}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="flex flex-col justify-between gap-4 rounded-mm-card border border-mm-border bg-mm-bg p-4 sm:flex-row sm:items-center">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={isVivaRequired}
                onChange={(e) => setIsVivaRequired(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
              />
              <div>
                <span className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-heading">
                  <Sparkles className="h-4 w-4 text-mm-blue-hover" />
                  <span>Bắt buộc vấn đáp tự động Viva Sandbox sau khi nộp bài</span>
                </span>
                <span className="mt-0.5 block font-mm-ui text-xs text-mm-text-secondary">
                  Hệ thống sinh câu hỏi trực tiếp từ sản phẩm bài nộp để xác thực năng lực thực tế
                </span>
              </div>
            </label>

            {isVivaRequired && (
              <div className="flex shrink-0 items-center gap-2">
                <label
                  htmlFor="assignment-viva-count"
                  className="font-mm-ui text-xs font-medium text-mm-text-secondary"
                >
                  Số câu hỏi:
                </label>
                <input
                  id="assignment-viva-count"
                  type="number"
                  min={1}
                  max={10}
                  value={vivaQuestionCount}
                  onChange={(e) => setVivaQuestionCount(Number(e.target.value))}
                  className={clsx(mmInputClass(false), "w-20 text-center")}
                />
              </div>
            )}
          </div>
        </section>
      </div>
    </MmModal>
  );
};
