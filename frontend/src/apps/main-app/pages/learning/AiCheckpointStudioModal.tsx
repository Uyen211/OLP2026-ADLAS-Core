/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle2,
  Loader2,
  Pencil,
  Quote,
  Sparkles,
  X,
} from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LOResponse } from "../../../../types/course";
import type {
  CheckpointCreatePayload,
  CheckpointSuggestion,
  DocumentSection,
  LearningMaterial,
} from "../../../../types/learning";
import { BloomBadge } from "../../components/BloomBadge";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";

export interface AiCheckpointStudioModalProps {
  open: boolean;
  courseId: string;
  material: LearningMaterial | null;
  availableLos: LOResponse[];
  onClose: () => void;
}

const BLOOM_OPTIONS: Array<{
  value: "REMEMBER" | "UNDERSTAND" | "APPLY";
  label: string;
  desc: string;
}> = [
  {
    value: "REMEMBER",
    label: "Nhận biết",
    desc: "Kiểm tra định nghĩa, khái niệm cơ bản",
  },
  {
    value: "UNDERSTAND",
    label: "Thông hiểu",
    desc: "Giải thích nguyên lý, so sánh",
  },
  {
    value: "APPLY",
    label: "Vận dụng",
    desc: "Tình huống thực tế, phân tích vấn đề",
  },
];

export const AiCheckpointStudioModal: React.FC<AiCheckpointStudioModalProps> = ({
  open,
  courseId,
  material,
  availableLos,
  onClose,
}) => {
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [loadingSections, setLoadingSections] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [selectedSectionIds, setSelectedSectionIds] = useState<number[]>([]);

  const [bloomLevel, setBloomLevel] = useState<"REMEMBER" | "UNDERSTAND" | "APPLY">(
    "UNDERSTAND"
  );
  const [numQuestions, setNumQuestions] = useState<number>(3);
  const [loId, setLoId] = useState<string>("");

  const [generating, setGenerating] = useState(false);
  const [suggestions, setSuggestions] = useState<CheckpointSuggestion[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || !material) return;
    setSections([]);
    setSelectedSectionIds([]);
    setSuggestions([]);
    setScanError(null);
    setEditingId(null);
    setLoId(material.lo_id || "");

    setLoadingSections(true);
    learningService
      .getMaterialSections(courseId, material.id)
      .then((res) => {
        setSections(res.sections);
        if (res.sections.length > 0) {
          setSelectedSectionIds([res.sections[0].section_id]);
        }
      })
      .catch((err) => {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Không thể bóc tách cấu trúc tài liệu.";
        setScanError(msg);
      })
      .finally(() => setLoadingSections(false));
  }, [open, courseId, material]);

  if (!open || !material) return null;

  const toggleSection = (id: number) => {
    setSelectedSectionIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectedWords = sections
    .filter((s) => selectedSectionIds.includes(s.section_id))
    .reduce((acc, s) => acc + s.word_count, 0);

  const handleGenerate = async () => {
    if (selectedSectionIds.length === 0) {
      showToast("warning", "Vui lòng tích chọn ít nhất một phân đoạn.");
      return;
    }
    if (selectedWords < 100) {
      showToast(
        "warning",
        "Mục được chọn quá ít nội dung thông tin (dưới 100 từ). Vui lòng chọn phân đoạn dài hơn hoặc gộp chung với mục kế bên."
      );
      return;
    }

    setGenerating(true);
    setSuggestions([]);
    try {
      const res = await learningService.generateCheckpointSuggestions(
        courseId,
        material.id,
        {
          section_ids: selectedSectionIds,
          bloom_level: bloomLevel,
          num_questions: numQuestions,
          lo_id: loId || null,
        }
      );
      setSuggestions(res.suggestions);
      if (res.suggestions.length === 0) {
        showToast(
          "warning",
          "AI chưa tạo được câu hỏi có bằng chứng trích dẫn khớp hoàn toàn. Vui lòng thử lại."
        );
      }
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Lỗi khi sinh câu hỏi gợi ý."
      );
    } finally {
      setGenerating(false);
    }
  };

  const toCheckpointPayload = (s: CheckpointSuggestion): CheckpointCreatePayload => ({
    question_text: s.question_text,
    question_type: "MULTIPLE_CHOICE",
    section_index: s.citation_page,
    options: s.options,
    correct_option: s.correct_option,
    expected_concept: s.evidence_quote,
    bloom_level: s.bloom_level,
    source_citation: `${s.citation}: "${s.evidence_quote}"`,
    lo_id: s.lo_id || (loId ? loId : null),
    is_blocking: true,
    time_limit_seconds: 15,
    rewind_seconds: 0,
  });

  const handleApproveOne = async (s: CheckpointSuggestion) => {
    setSaving(true);
    try {
      await learningService.batchCreateCheckpoints(courseId, material.id, [
        toCheckpointPayload(s),
      ]);
      setSuggestions((prev) => prev.filter((item) => item.temp_id !== s.temp_id));
      showToast("success", "Đã thêm thành công câu hỏi vào bài học!");
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể lưu câu hỏi."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleApproveAll = async () => {
    if (suggestions.length === 0) return;
    setSaving(true);
    try {
      const res = await learningService.batchCreateCheckpoints(
        courseId,
        material.id,
        suggestions.map(toCheckpointPayload)
      );
      setSuggestions([]);
      showToast(
        "success",
        `Đã thêm thành công ${res.created_count} câu hỏi vào bài học!`
      );
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể lưu danh sách câu hỏi."
      );
    } finally {
      setSaving(false);
    }
  };

  const updateSuggestionField = (
    tempId: string,
    updater: (prev: CheckpointSuggestion) => CheckpointSuggestion
  ) => {
    setSuggestions((prev) =>
      prev.map((item) => (item.temp_id === tempId ? updater(item) : item))
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Bóc Tách Slide/PDF & Gợi Ý Câu Hỏi 1-Click
              </h3>
              <p className="text-xs text-slate-500">{material.title}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        {loadingSections ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 py-20 text-slate-500">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-sm font-medium">
              Đang đọc và phân tích cấu trúc chương mục tài liệu...
            </p>
          </div>
        ) : scanError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
            <div className="rounded-full bg-amber-100 p-3 text-amber-600">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <h4 className="text-base font-bold text-slate-900">
              Không thể bóc tách tài liệu tự động
            </h4>
            <p className="max-w-lg text-sm text-slate-600">{scanError}</p>
            <MmButton variant="secondary" onClick={onClose}>
              Đóng
            </MmButton>
          </div>
        ) : (
          <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-12">
            {/* Left Column: Detected Sections */}
            <div className="flex flex-col border-b border-slate-200 bg-slate-50/60 lg:col-span-5 lg:border-b-0 lg:border-r">
              <div className="border-b border-slate-200 px-5 py-3">
                <h4 className="flex items-center gap-2 text-sm font-bold text-slate-800">
                  <BookOpen className="h-4 w-4 text-blue-600" />
                  <span>Cây Phân Đoạn / Chương Mục ({sections.length})</span>
                </h4>
              </div>
              <div className="flex-1 space-y-2.5 overflow-y-auto p-4">
                {sections.map((sec) => {
                  const checked = selectedSectionIds.includes(sec.section_id);
                  return (
                    <label
                      key={sec.section_id}
                      className={`block cursor-pointer rounded-xl border p-3.5 transition-all ${
                        checked
                          ? "border-blue-500 bg-blue-50/70 shadow-sm"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleSection(sec.section_id)}
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-slate-900">
                              {sec.title}
                            </span>
                            <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                              {sec.word_count} từ
                            </span>
                          </div>
                          {sec.summary && (
                            <p className="mt-1 text-xs leading-relaxed text-slate-600">
                              {sec.summary}
                            </p>
                          )}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Controls & Question Preview Cards */}
            <div className="flex flex-col overflow-hidden lg:col-span-7">
              <div className="space-y-4 border-b border-slate-200 bg-white p-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-600">
                      Mức độ nhận thức (Bloom)
                    </label>
                    <div className="space-y-1.5">
                      {BLOOM_OPTIONS.map((opt) => (
                        <label
                          key={opt.value}
                          className="flex cursor-pointer items-center gap-2 text-xs"
                        >
                          <input
                            type="radio"
                            name="bloomLevel"
                            checked={bloomLevel === opt.value}
                            onChange={() => setBloomLevel(opt.value)}
                            className="text-blue-600"
                          />
                          <span className="font-semibold text-slate-800">
                            {opt.label}
                          </span>
                          <span className="text-slate-500">({opt.desc})</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-600">
                        Số lượng câu hỏi
                      </label>
                      <select
                        value={numQuestions}
                        onChange={(e) => setNumQuestions(Number(e.target.value))}
                        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                      >
                        <option value={1}>1 câu</option>
                        <option value={2}>2 câu</option>
                        <option value={3}>3 câu</option>
                        <option value={5}>5 câu</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-600">
                        Chuẩn đầu ra (LO)
                      </label>
                      <select
                        value={loId}
                        onChange={(e) => setLoId(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                      >
                        <option value="">-- Không gắn LO cụ thể --</option>
                        {availableLos.map((lo) => (
                          <option key={lo.id} value={lo.id}>
                            {lo.code} - {lo.description}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-slate-500">
                    Đã chọn {selectedSectionIds.length} phân đoạn ({selectedWords} từ)
                  </span>
                  <MmButton
                    variant="brand"
                    onClick={handleGenerate}
                    disabled={generating || selectedSectionIds.length === 0}
                  >
                    {generating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    <span>
                      {generating
                        ? "Đang phân tích nội dung và soạn thảo câu hỏi..."
                        : "Tạo Câu Hỏi Gợi Ý"}
                    </span>
                  </MmButton>
                </div>
              </div>

              {/* Preview Cards */}
              <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-5">
                {suggestions.length > 0 && (
                  <div className="flex items-center justify-between pb-1">
                    <h4 className="text-sm font-bold text-slate-800">
                      Câu hỏi gợi ý ({suggestions.length})
                    </h4>
                    <MmButton
                      variant="brand"
                      size="sm"
                      disabled={saving}
                      onClick={handleApproveAll}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Duyệt Tất Cả {suggestions.length} Câu</span>
                    </MmButton>
                  </div>
                )}

                {suggestions.map((s) => {
                  const isEditing = editingId === s.temp_id;
                  return (
                    <div
                      key={s.temp_id}
                      className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <BloomBadge level={s.bloom_level} />
                        <div className="flex items-center gap-1.5">
                          <MmButton
                            variant="secondary"
                            size="sm"
                            onClick={() =>
                              setEditingId(isEditing ? null : s.temp_id)
                            }
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            <span>
                              {isEditing ? "Lưu thay đổi" : "Chỉnh sửa nhanh"}
                            </span>
                          </MmButton>
                          <MmButton
                            variant="brand"
                            size="sm"
                            disabled={saving}
                            onClick={() => handleApproveOne(s)}
                          >
                            <Check className="h-3.5 w-3.5" />
                            <span>Duyệt 1-Click</span>
                          </MmButton>
                        </div>
                      </div>

                      {isEditing ? (
                        <textarea
                          value={s.question_text}
                          onChange={(e) =>
                            updateSuggestionField(s.temp_id, (prev) => ({
                              ...prev,
                              question_text: e.target.value,
                            }))
                          }
                          rows={2}
                          className="w-full rounded-lg border border-blue-300 p-2 text-sm font-medium"
                        />
                      ) : (
                        <p className="text-sm font-semibold text-slate-900">
                          {s.question_text}
                        </p>
                      )}

                      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                        {(["A", "B", "C", "D"] as const).map((key) => {
                          const isCorrect = s.correct_option === key;
                          return (
                            <div
                              key={key}
                              className={`rounded-lg border px-3 py-1.5 text-xs ${
                                isCorrect
                                  ? "border-emerald-500 bg-emerald-50 font-semibold text-emerald-900"
                                  : "border-slate-200 bg-slate-50 text-slate-700"
                              }`}
                            >
                              {isEditing ? (
                                <input
                                  type="text"
                                  value={s.options[key] || ""}
                                  onChange={(e) =>
                                    updateSuggestionField(s.temp_id, (prev) => ({
                                      ...prev,
                                      options: {
                                        ...prev.options,
                                        [key]: e.target.value,
                                      },
                                    }))
                                  }
                                  className="w-full bg-transparent outline-none"
                                />
                              ) : (
                                <span>
                                  <strong>{key}.</strong> {s.options[key]}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      <div className="flex items-start gap-2 rounded-lg bg-blue-50/70 px-3 py-2 text-xs text-blue-900">
                        <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600" />
                        <div>
                          <span className="font-bold">{s.citation}: </span>
                          <span className="italic">"{s.evidence_quote}"</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
