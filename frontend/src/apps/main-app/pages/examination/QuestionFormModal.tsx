/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, Eye, EyeOff, Plus, Trash2 } from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type { BloomLevel, LOResponse } from "../../../../types/course";
import type {
  QuestionBankResponse,
  QuestionResponse,
  QuestionType,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MathCodeContent } from "../../components/MathCodeContent";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import { BLOOM_OPTIONS, toNumeric } from "./examHelpers";

interface OptionDraft {
  key: string;
  text: string;
  is_correct: boolean;
}

const DEFAULT_KEYS = ["A", "B", "C", "D", "E", "F"];

export interface QuestionFormModalProps {
  open: boolean;
  courseId: string;
  banks: QuestionBankResponse[];
  learningObjectives: LOResponse[];
  editingQuestion?: QuestionResponse | null;
  defaultBankId?: string;
  onClose: () => void;
  onSaved: (question: QuestionResponse) => void;
}

export const QuestionFormModal: React.FC<QuestionFormModalProps> = ({
  open,
  courseId,
  banks,
  learningObjectives,
  editingQuestion,
  defaultBankId,
  onClose,
  onSaved,
}) => {
  const [bankId, setBankId] = useState("");
  const [loId, setLoId] = useState("");
  const [bloomLevel, setBloomLevel] = useState<BloomLevel>("UNDERSTAND");
  const [questionType, setQuestionType] = useState<QuestionType>("MULTIPLE_CHOICE");
  const [defaultPoints, setDefaultPoints] = useState("1");
  const [questionText, setQuestionText] = useState("");
  const [explanation, setExplanation] = useState("");
  const [options, setOptions] = useState<OptionDraft[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingQuestion) {
      setBankId(editingQuestion.bank_id);
      setLoId(editingQuestion.lo_id ?? "");
      setBloomLevel(editingQuestion.bloom_level);
      setQuestionType(editingQuestion.question_type);
      setDefaultPoints(String(toNumeric(editingQuestion.default_points, 1)));
      setQuestionText(editingQuestion.question_text);
      setExplanation(editingQuestion.explanation ?? "");
      setOptions(
        editingQuestion.options.map((opt, idx) => ({
          key: opt.key || DEFAULT_KEYS[idx] || String(idx + 1),
          text: opt.text || "",
          is_correct: Boolean(opt.is_correct),
        }))
      );
    } else {
      setBankId(defaultBankId || banks[0]?.id || "");
      setLoId("");
      setBloomLevel("UNDERSTAND");
      setQuestionType("MULTIPLE_CHOICE");
      setDefaultPoints("1");
      setQuestionText("");
      setExplanation("");
      setOptions([
        { key: "A", text: "", is_correct: true },
        { key: "B", text: "", is_correct: false },
        { key: "C", text: "", is_correct: false },
        { key: "D", text: "", is_correct: false },
      ]);
    }
    setShowPreview(false);
    setBannerError(null);
  }, [open, editingQuestion, banks, defaultBankId]);

  const handleToggleCorrect = (index: number) => {
    setOptions((prev) =>
      prev.map((opt, idx) => {
        if (questionType === "MULTIPLE_CHOICE") {
          return { ...opt, is_correct: idx === index };
        }
        return idx === index ? { ...opt, is_correct: !opt.is_correct } : opt;
      })
    );
  };

  const handleTypeChange = (nextType: QuestionType) => {
    setQuestionType(nextType);
    if (nextType === "MULTIPLE_CHOICE") {
      const firstCorrectIdx = options.findIndex((o) => o.is_correct);
      const keepIdx = firstCorrectIdx >= 0 ? firstCorrectIdx : 0;
      setOptions((prev) =>
        prev.map((opt, idx) => ({ ...opt, is_correct: idx === keepIdx }))
      );
    }
  };

  const handleAddOption = () => {
    if (options.length >= 6) return;
    const nextKey = DEFAULT_KEYS[options.length] || `P${options.length + 1}`;
    setOptions((prev) => [...prev, { key: nextKey, text: "", is_correct: false }]);
  };

  const handleRemoveOption = (index: number) => {
    if (options.length <= 2) return;
    setOptions((prev) =>
      prev
        .filter((_, idx) => idx !== index)
        .map((opt, idx) => ({
          ...opt,
          key: DEFAULT_KEYS[idx] || opt.key,
        }))
    );
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBannerError(null);

    if (!bankId) {
      setBannerError("Vui lòng chọn chương / danh mục ngân hàng câu hỏi.");
      return;
    }
    if (questionText.trim().length < 3) {
      setBannerError("Nội dung câu hỏi phải có ít nhất 3 ký tự.");
      return;
    }
    const pts = Number(defaultPoints);
    if (Number.isNaN(pts) || pts <= 0 || pts > 99.99) {
      setBannerError("Điểm mặc định phải lớn hơn 0 và nhỏ hơn hoặc bằng 99.99.");
      return;
    }

    const cleanedOptions = options.map((o) => ({
      key: o.key.trim().toUpperCase(),
      text: o.text.trim(),
      is_correct: o.is_correct,
    }));

    if (cleanedOptions.length < 2) {
      setBannerError("Câu hỏi phải có ít nhất 2 phương án trả lời.");
      return;
    }
    if (cleanedOptions.some((o) => !o.text)) {
      setBannerError("Vui lòng nhập đầy đủ nội dung cho tất cả phương án trả lời.");
      return;
    }
    const correctCount = cleanedOptions.filter((o) => o.is_correct).length;
    if (questionType === "MULTIPLE_CHOICE" && correctCount !== 1) {
      setBannerError("Câu hỏi trắc nghiệm 1 đáp án phải có đúng 1 phương án đúng.");
      return;
    }
    if (questionType === "MULTI_SELECT" && correctCount < 1) {
      setBannerError("Câu hỏi chọn nhiều đáp án phải có ít nhất 1 phương án đúng.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        bank_id: bankId,
        lo_id: loId || null,
        bloom_level: bloomLevel,
        question_text: questionText.trim(),
        question_type: questionType,
        default_points: pts,
        options: cleanedOptions,
        explanation: explanation.trim() || null,
      };

      const saved = editingQuestion
        ? await examinationService.updateQuestion(editingQuestion.id, payload)
        : await examinationService.createQuestion(courseId, payload);

      showToast(
        "success",
        editingQuestion
          ? "Đã cập nhật câu hỏi trong ngân hàng."
          : "Đã thêm câu hỏi mới vào ngân hàng."
      );
      onSaved(saved);
      onClose();
    } catch (err) {
      setBannerError(
        err instanceof ApiError
          ? err.message
          : "Không thể lưu câu hỏi. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title={editingQuestion ? "Chỉnh sửa câu hỏi" : "Soạn câu hỏi mới"}
      subtitle="Hỗ trợ công thức Toán KaTeX ($...$, $$...$$) và khối mã nguồn (```...```)"
      maxWidthClass="max-w-3xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton type="submit" form="question-form" variant="brand" loading={loading}>
            {editingQuestion ? "Lưu thay đổi" : "Tạo câu hỏi"}
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

      <form id="question-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Chương / Danh mục ngân hàng" htmlFor="q-bank" required>
            <select
              id="q-bank"
              value={bankId}
              onChange={(e) => setBankId(e.target.value)}
              className={mmInputClass(false)}
            >
              <option value="">-- Chọn danh mục --</option>
              {banks.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.category_name} ({b.question_count} câu)
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Chuẩn đầu ra (LO)" htmlFor="q-lo">
            <select
              id="q-lo"
              value={loId}
              onChange={(e) => setLoId(e.target.value)}
              className={mmInputClass(false)}
            >
              <option value="">Không gắn chuẩn đầu ra</option>
              {learningObjectives.map((lo) => (
                <option key={lo.id} value={lo.id}>
                  {lo.code} - {lo.description}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Mức độ Bloom" htmlFor="q-bloom" required>
            <select
              id="q-bloom"
              value={bloomLevel}
              onChange={(e) => setBloomLevel(e.target.value as BloomLevel)}
              className={mmInputClass(false)}
            >
              {BLOOM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Loại câu hỏi" htmlFor="q-type" required>
            <select
              id="q-type"
              value={questionType}
              onChange={(e) => handleTypeChange(e.target.value as QuestionType)}
              className={mmInputClass(false)}
            >
              <option value="MULTIPLE_CHOICE">Trắc nghiệm 1 đáp án</option>
              <option value="MULTI_SELECT">Chọn nhiều đáp án</option>
            </select>
          </FormField>

          <FormField label="Điểm mặc định" htmlFor="q-points" required>
            <input
              id="q-points"
              type="number"
              min={0.25}
              max={99.99}
              step="0.25"
              value={defaultPoints}
              onChange={(e) => setDefaultPoints(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label
              htmlFor="q-text"
              className="font-mm-ui text-sm font-medium text-mm-heading"
            >
              Nội dung câu hỏi <span className="text-mm-danger">*</span>
            </label>
            <button
              type="button"
              onClick={() => setShowPreview((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-mm-tag px-2.5 py-1 font-mm-ui text-xs font-medium text-mm-blue-hover hover:bg-mm-blue-light/20"
            >
              {showPreview ? (
                <>
                  <EyeOff className="h-3.5 w-3.5" />
                  <span>Ẩn xem trước</span>
                </>
              ) : (
                <>
                  <Eye className="h-3.5 w-3.5" />
                  <span>Xem trước KaTeX / Code</span>
                </>
              )}
            </button>
          </div>
          <textarea
            id="q-text"
            rows={4}
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="Ví dụ: Độ phức tạp thời gian của thuật toán QuickSort trong trường hợp trung bình là $O(n \log n)$..."
            className={mmInputClass(false)}
          />
          {showPreview && questionText.trim() && (
            <div className="mt-2 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3.5">
              <p className="mb-1.5 font-mm-ui text-xs font-medium text-mm-text-muted">
                Xem trước hiển thị
              </p>
              <MathCodeContent content={questionText} />
            </div>
          )}
        </div>

        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-mm-ui text-sm font-medium text-mm-heading">
              Các phương án trả lời{" "}
              <span className="font-normal text-mm-text-muted">
                (
                {questionType === "MULTIPLE_CHOICE"
                  ? "chọn đúng 1 đáp án đúng"
                  : "chọn 1 hoặc nhiều đáp án đúng"}
                )
              </span>
            </span>
            {options.length < 6 && (
              <MmButton variant="secondary" size="sm" onClick={handleAddOption}>
                <Plus className="h-3.5 w-3.5" />
                <span>Thêm phương án</span>
              </MmButton>
            )}
          </div>

          <div className="space-y-2">
            {options.map((opt, idx) => (
              <div
                key={`${opt.key}-${idx}`}
                className="flex items-center gap-2.5 rounded-mm-panel border border-mm-border bg-mm-bg p-2.5"
              >
                <input
                  type={questionType === "MULTIPLE_CHOICE" ? "radio" : "checkbox"}
                  name="correct-option"
                  checked={opt.is_correct}
                  onChange={() => handleToggleCorrect(idx)}
                  aria-label={`Đánh dấu phương án ${opt.key} là đáp án đúng`}
                  className="h-4 w-4 cursor-pointer accent-mm-blue-hover"
                />
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-mm-divider font-mm-mono text-xs font-medium text-mm-heading">
                  {opt.key}
                </span>
                <input
                  type="text"
                  value={opt.text}
                  onChange={(e) => {
                    const val = e.target.value;
                    setOptions((prev) =>
                      prev.map((item, i) => (i === idx ? { ...item, text: val } : item))
                    );
                  }}
                  placeholder={`Nhập nội dung phương án ${opt.key} (hỗ trợ $...$ và \`code\`)`}
                  className={mmInputClass(false)}
                />
                {options.length > 2 && (
                  <button
                    type="button"
                    title="Xóa phương án"
                    onClick={() => handleRemoveOption(idx)}
                    className="rounded-mm-tag p-1.5 text-mm-text-muted hover:bg-mm-danger-bg hover:text-mm-danger"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <FormField
          label="Lời giải thích đáp án (tùy chọn)"
          htmlFor="q-explanation"
          helper="Hiển thị cho sinh viên sau khi điểm được công bố theo chính sách đề thi"
        >
          <textarea
            id="q-explanation"
            rows={2}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Giải thích lý do đáp án đúng hoặc công thức tính toán..."
            className={mmInputClass(false)}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
