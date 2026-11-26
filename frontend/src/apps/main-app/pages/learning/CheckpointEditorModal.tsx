/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { BookmarkCheck, Clock, Loader2, Pencil, Plus, Trash2, X } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LearningMaterial, MaterialCheckpoint } from "../../../../types/learning";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";

export interface CheckpointEditorModalProps {
  open: boolean;
  courseId: string;
  material: LearningMaterial | null;
  onClose: () => void;
}

function formatSeconds(secs?: number | null): string {
  if (secs === null || secs === undefined) return "00:00";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export const CheckpointEditorModal: React.FC<CheckpointEditorModalProps> = ({
  open,
  courseId,
  material,
  onClose,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [checkpoints, setCheckpoints] = useState<MaterialCheckpoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [questionText, setQuestionText] = useState("");
  const [stopTimeSeconds, setStopTimeSeconds] = useState<number>(10);
  const [sectionIndex, setSectionIndex] = useState<number>(1);
  const [optA, setOptA] = useState("");
  const [optB, setOptB] = useState("");
  const [optC, setOptC] = useState("");
  const [optD, setOptD] = useState("");
  const [correctOption, setCorrectOption] = useState("A");
  const [timeLimitSeconds, setTimeLimitSeconds] = useState(10);
  const [rewindSeconds, setRewindSeconds] = useState(15);
  const [isBlocking, setIsBlocking] = useState(true);

  const isVideo = material?.material_type === "VIDEO";

  const resetForm = useCallback(() => {
    setEditingId(null);
    setQuestionText("");
    setStopTimeSeconds(10);
    setSectionIndex(1);
    setOptA("");
    setOptB("");
    setOptC("");
    setOptD("");
    setCorrectOption("A");
    setTimeLimitSeconds(10);
    setRewindSeconds(15);
    setIsBlocking(true);
  }, []);

  const loadCheckpoints = useCallback(async () => {
    if (!material) return;
    setLoading(true);
    try {
      const list = await learningService.listCheckpoints(courseId, material.id);
      setCheckpoints(list);
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể tải danh sách điểm dừng.");
    } finally {
      setLoading(false);
    }
  }, [courseId, material]);

  useEffect(() => {
    if (!open || !material) return;
    resetForm();
    loadCheckpoints();

    let createdUrl: string | null = null;
    if (isVideo && material.file_url) {
      if (material.file_url.startsWith("http")) {
        setVideoUrl(material.file_url);
      } else {
        learningService
          .fetchMaterialPreviewBlob(courseId, material.id)
          .then(({ blob }) => {
            createdUrl = URL.createObjectURL(blob);
            setVideoUrl(createdUrl);
          })
          .catch(() => setVideoUrl(null));
      }
    } else {
      setVideoUrl(null);
    }

    return () => {
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [open, material, isVideo, courseId, loadCheckpoints, resetForm]);

  if (!open || !material) return null;

  const handleCaptureCurrentTime = () => {
    if (videoRef.current) {
      setStopTimeSeconds(Math.floor(videoRef.current.currentTime));
    }
  };

  const handleEdit = (chk: MaterialCheckpoint) => {
    setEditingId(chk.id);
    setQuestionText(chk.question_text);
    setStopTimeSeconds(chk.stop_time_seconds ?? 10);
    setSectionIndex(chk.section_index ?? 1);
    setOptA(chk.options?.A || "");
    setOptB(chk.options?.B || "");
    setOptC(chk.options?.C || "");
    setOptD(chk.options?.D || "");
    setCorrectOption(chk.correct_option || "A");
    setTimeLimitSeconds(chk.time_limit_seconds ?? 10);
    setRewindSeconds(chk.rewind_seconds ?? 15);
    setIsBlocking(chk.is_blocking);
  };

  const handleDelete = async (checkpointId: string) => {
    try {
      await learningService.deleteCheckpoint(courseId, checkpointId);
      showToast("success", "Đã xóa điểm dừng kiểm tra.");
      if (editingId === checkpointId) resetForm();
      await loadCheckpoints();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể xóa điểm dừng.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (questionText.trim().length < 5) {
      showToast("error", "Nội dung câu hỏi tối thiểu 5 ký tự.");
      return;
    }
    if (!optA.trim() || !optB.trim() || !optC.trim() || !optD.trim()) {
      showToast("error", "Vui lòng nhập đầy đủ 4 phương án A, B, C, D.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        question_text: questionText.trim(),
        stop_time_seconds: isVideo ? stopTimeSeconds : null,
        section_index: isVideo ? null : sectionIndex,
        options: { A: optA.trim(), B: optB.trim(), C: optC.trim(), D: optD.trim() },
        correct_option: correctOption,
        time_limit_seconds: timeLimitSeconds,
        rewind_seconds: isVideo ? rewindSeconds : 0,
        is_blocking: isBlocking,
      };

      if (editingId) {
        await learningService.updateCheckpoint(courseId, editingId, payload);
        showToast("success", "Đã cập nhật điểm dừng kiểm tra.");
      } else {
        await learningService.createCheckpoint(courseId, material.id, payload);
        showToast("success", "Đã thêm điểm dừng kiểm tra mới.");
      }
      resetForm();
      await loadCheckpoints();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể lưu điểm dừng.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-mm border border-mm-border bg-mm-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-mm-divider bg-mm-surface-alt/40 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <BookmarkCheck className="h-5 w-5 text-mm-brand" />
            <div>
              <h3 className="font-mm-mid text-base font-semibold text-mm-heading">
                Biên tập Điểm dừng Kiểm tra ({material.material_type})
              </h3>
              <p className="text-xs text-mm-text-muted">{material.title}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-mm p-1.5 text-mm-text-muted hover:bg-mm-surface-alt hover:text-mm-heading"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="grid flex-1 grid-cols-1 gap-5 overflow-y-auto p-5 lg:grid-cols-12">
          {/* Left: Video preview + Checkpoint list */}
          <div className="space-y-4 lg:col-span-6">
            {isVideo && videoUrl && (
              <div className="space-y-2 rounded-mm border border-mm-divider bg-mm-bg p-3">
                <video ref={videoRef} controls src={videoUrl} className="w-full rounded bg-black" />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-mm-text-muted">
                    Phát video tới mốc mong muốn rồi bấm nút bên cạnh:
                  </span>
                  <MmButton type="button" size="sm" variant="secondary" onClick={handleCaptureCurrentTime}>
                    <Clock className="h-3.5 w-3.5" />
                    <span>Lấy giây hiện tại</span>
                  </MmButton>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-mm-heading">
                Danh sách câu hỏi ({checkpoints.length})
              </h4>
              {loading ? (
                <div className="flex items-center gap-2 py-6 text-xs text-mm-text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Đang tải...</span>
                </div>
              ) : checkpoints.length === 0 ? (
                <div className="rounded-mm border border-dashed border-mm-border p-6 text-center text-xs text-mm-text-muted">
                  Chưa có điểm dừng kiểm tra nào cho học liệu này.
                </div>
              ) : (
                <div className="space-y-2">
                  {checkpoints.map((chk) => (
                    <div
                      key={chk.id}
                      className="flex items-start justify-between gap-2 rounded-mm border border-mm-divider bg-mm-surface-alt/30 p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                          <span className="rounded bg-amber-500/15 px-2 py-0.5 font-mm-mono font-semibold text-amber-600">
                            {isVideo ? formatSeconds(chk.stop_time_seconds) : `Mục ${chk.section_index ?? 1}`}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                              chk.is_blocking
                                ? "bg-red-500/10 text-red-600"
                                : "bg-slate-500/10 text-slate-500"
                            }`}
                          >
                            {chk.is_blocking ? "Bắt buộc" : "Tùy chọn"}
                          </span>
                          <span className="text-mm-text-muted">Đáp án: {chk.correct_option}</span>
                        </div>
                        <p className="mt-1.5 text-xs font-medium text-mm-heading">{chk.question_text}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleEdit(chk)}
                          className="rounded p-1 text-mm-text-muted hover:bg-mm-surface-alt hover:text-mm-heading"
                          title="Chỉnh sửa"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(chk.id)}
                          className="rounded p-1 text-mm-error hover:bg-mm-error-bg"
                          title="Xóa"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Create/Edit Form */}
          <form onSubmit={handleSubmit} className="space-y-3 rounded-mm border border-mm-divider bg-mm-bg/40 p-4 lg:col-span-6">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-mm-heading">
                {editingId ? "Cập nhật điểm dừng" : "Thêm điểm dừng mới"}
              </h4>
              {editingId && (
                <button type="button" onClick={resetForm} className="text-xs text-mm-brand hover:underline">
                  Hủy sửa (Tạo mới)
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              {isVideo ? (
                <div>
                  <label className="mb-1 block text-xs font-medium text-mm-heading">
                    Mốc giây dừng (giây)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={stopTimeSeconds}
                    onChange={(e) => setStopTimeSeconds(Number(e.target.value))}
                    className="w-full rounded-mm border border-mm-border bg-mm-surface px-3 py-1.5 text-sm text-mm-heading"
                  />
                </div>
              ) : (
                <div>
                  <label className="mb-1 block text-xs font-medium text-mm-heading">
                    Đề mục / Trang số
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={sectionIndex}
                    onChange={(e) => setSectionIndex(Number(e.target.value))}
                    className="w-full rounded-mm border border-mm-border bg-mm-surface px-3 py-1.5 text-sm text-mm-heading"
                  />
                </div>
              )}

              <div>
                <label className="mb-1 block text-xs font-medium text-mm-heading">
                  Đếm ngược (giây)
                </label>
                <select
                  value={timeLimitSeconds}
                  onChange={(e) => setTimeLimitSeconds(Number(e.target.value))}
                  className="w-full rounded-mm border border-mm-border bg-mm-surface px-3 py-1.5 text-sm text-mm-heading"
                >
                  <option value={10}>10 giây (Mặc định)</option>
                  <option value={15}>15 giây</option>
                  <option value={20}>20 giây</option>
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-mm-heading">Nội dung câu hỏi</label>
              <textarea
                rows={2}
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder="Nhập câu hỏi kiểm tra nhanh kiến thức..."
                className="w-full rounded-mm border border-mm-border bg-mm-surface px-3 py-1.5 text-sm text-mm-heading"
              />
            </div>

            <div className="grid grid-cols-1 gap-2">
              {[
                { key: "A", val: optA, set: setOptA },
                { key: "B", val: optB, set: setOptB },
                { key: "C", val: optC, set: setOptC },
                { key: "D", val: optD, set: setOptD },
              ].map((item) => (
                <div key={item.key} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="correctOption"
                    checked={correctOption === item.key}
                    onChange={() => setCorrectOption(item.key)}
                    title={`Chọn ${item.key} là đáp án đúng`}
                  />
                  <span className="w-5 text-xs font-bold text-mm-heading">{item.key}.</span>
                  <input
                    type="text"
                    value={item.val}
                    onChange={(e) => item.set(e.target.value)}
                    placeholder={`Phương án ${item.key}`}
                    className="flex-1 rounded-mm border border-mm-border bg-mm-surface px-2.5 py-1 text-xs text-mm-heading"
                  />
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 text-xs text-mm-heading">
                <input
                  type="checkbox"
                  checked={isBlocking}
                  onChange={(e) => setIsBlocking(e.target.checked)}
                />
                <span>Bắt buộc vượt qua mới được mở khóa bài sau</span>
              </label>

              {isVideo && (
                <div className="flex items-center gap-1.5 text-xs text-mm-text-muted">
                  <span>Lùi khi sai:</span>
                  <input
                    type="number"
                    min={0}
                    max={60}
                    value={rewindSeconds}
                    onChange={(e) => setRewindSeconds(Number(e.target.value))}
                    className="w-14 rounded border border-mm-border bg-mm-surface px-2 py-0.5 text-xs text-mm-heading"
                  />
                  <span>s</span>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <MmButton type="submit" variant="primary" size="sm" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                <span>{editingId ? "Cập nhật điểm dừng" : "Lưu điểm dừng"}</span>
              </MmButton>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
