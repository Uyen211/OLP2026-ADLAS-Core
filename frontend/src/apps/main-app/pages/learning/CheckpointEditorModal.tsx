/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookmarkCheck,
  BookOpen,
  Check,
  CheckCircle2,
  Loader2,
  Pause,
  Pencil,
  Play,
  Plus,
  Quote,
  RotateCcw,
  RotateCw,
  Sparkles,
  Trash2,
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
  MaterialCheckpoint,
  MaterialStructuredContent,
} from "../../../../types/learning";
import { BloomBadge } from "../../components/BloomBadge";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";
import { DocumentFilmstripTrack } from "./DocumentFilmstripTrack";
import { DocumentSectionsStage } from "./DocumentSectionsStage";
import { SlidePdfStage } from "./SlidePdfStage";
import { VideoTimelineTrack, formatTimecode } from "./VideoTimelineTrack";

export interface CheckpointEditorModalProps {
  open: boolean;
  courseId: string;
  material: LearningMaterial | null;
  availableLos?: LOResponse[];
  onClose: () => void;
}

export const CheckpointEditorModal: React.FC<CheckpointEditorModalProps> = ({
  open,
  courseId,
  material,
  availableLos = [],
  onClose,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [checkpoints, setCheckpoints] = useState<MaterialCheckpoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  // Video studio playback state
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Document / PDF / Slide studio state
  const [structuredContent, setStructuredContent] = useState<MaterialStructuredContent | null>(null);
  const [structuredLoading, setStructuredLoading] = useState(false);
  const [currentPageIndex, setCurrentPageIndex] = useState(1);

  // Right-panel mode & selection
  const [panelMode, setPanelMode] = useState<"list" | "form" | "ai_distribute">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Form fields
  const [editingId, setEditingId] = useState<string | null>(null);
  const [questionText, setQuestionText] = useState("");
  const [stopTimeSeconds, setStopTimeSeconds] = useState<number>(0);
  const [sectionIndex, setSectionIndex] = useState<number>(1);
  const [optA, setOptA] = useState("");
  const [optB, setOptB] = useState("");
  const [optC, setOptC] = useState("");
  const [optD, setOptD] = useState("");
  const [correctOption, setCorrectOption] = useState("A");
  const [bloomLevel, setBloomLevel] = useState<"REMEMBER" | "UNDERSTAND" | "APPLY">("UNDERSTAND");
  const [sourceCitation, setSourceCitation] = useState("");
  const [loId, setLoId] = useState("");
  const [timeLimitSeconds, setTimeLimitSeconds] = useState(10);
  const [rewindSeconds, setRewindSeconds] = useState(15);
  const [isBlocking, setIsBlocking] = useState(true);
  const [suggestingPage, setSuggestingPage] = useState(false);

  // AI Distribute (Bloom Matrix) state
  const [sections, setSections] = useState<DocumentSection[]>([]);
  const [loadingSections, setLoadingSections] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [selectedSectionIds, setSelectedSectionIds] = useState<number[]>([]);
  const [bloomDist, setBloomDist] = useState<{ REMEMBER: number; UNDERSTAND: number; APPLY: number }>({
    REMEMBER: 2,
    UNDERSTAND: 2,
    APPLY: 1,
  });
  const [aiLoId, setAiLoId] = useState("");
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<CheckpointSuggestion[]>([]);
  const [editingTempId, setEditingTempId] = useState<string | null>(null);
  const [savingBatch, setSavingBatch] = useState(false);

  const isVideo = material?.material_type === "VIDEO";
  const supportsAiDoc =
    !isVideo && (material?.material_type === "PDF" || material?.material_type === "SLIDE");

  const sortedCheckpoints = useMemo(() => {
    return [...checkpoints].sort((a, b) => {
      if (isVideo) {
        return (a.stop_time_seconds ?? 0) - (b.stop_time_seconds ?? 0);
      }
      return (a.section_index ?? 1) - (b.section_index ?? 1);
    });
  }, [checkpoints, isVideo]);

  const resetForm = useCallback((initialStopSeconds = 0) => {
    setEditingId(null);
    setQuestionText("");
    setStopTimeSeconds(initialStopSeconds);
    setSectionIndex(1);
    setOptA("");
    setOptB("");
    setOptC("");
    setOptD("");
    setCorrectOption("A");
    setBloomLevel("UNDERSTAND");
    setSourceCitation("");
    setLoId(material?.lo_id || "");
    setTimeLimitSeconds(10);
    setRewindSeconds(15);
    setIsBlocking(true);
  }, [material?.lo_id]);

  const loadCheckpoints = useCallback(async () => {
    if (!material) return;
    setLoading(true);
    try {
      const list = await learningService.listCheckpoints(courseId, material.id);
      setCheckpoints(list);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải danh sách điểm dừng."
      );
    } finally {
      setLoading(false);
    }
  }, [courseId, material]);

  useEffect(() => {
    if (!open || !material) return;
    resetForm(0);
    setPanelMode("list");
    setSelectedId(null);
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
    setCurrentPageIndex(1);
    setStructuredContent(null);
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
      if (material.file_url && !material.file_url.startsWith("http")) {
        setStructuredLoading(true);
        learningService
          .getMaterialStructuredContent(courseId, material.id)
          .then((res) => setStructuredContent(res))
          .catch(() => setStructuredContent(null))
          .finally(() => setStructuredLoading(false));
      }
    }

    return () => {
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [open, material, isVideo, courseId, loadCheckpoints, resetForm]);

  if (!open || !material) return null;

  const seekVideoTo = (secs: number, pauseAfterSeek = false) => {
    const clamped = Math.max(0, duration > 0 ? Math.min(duration, secs) : secs);
    setCurrentTime(clamped);
    if (videoRef.current) {
      videoRef.current.currentTime = clamped;
      if (pauseAfterSeek) {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    }
  };

  const togglePlayPause = () => {
    const vid = videoRef.current;
    if (!vid) return;
    if (vid.paused) {
      vid.play().catch(() => {});
      setIsPlaying(true);
    } else {
      vid.pause();
      setIsPlaying(false);
    }
  };

  const handleOpenAddAtCurrentTime = () => {
    if (videoRef.current && !videoRef.current.paused) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
    const sec = Math.floor(currentTime);
    resetForm(sec);
    setSelectedId(null);
    setPanelMode("form");
  };

  const handleOpenAddAtSection = (targetSection: number) => {
    resetForm(0);
    setSectionIndex(targetSection);
    setSelectedId(null);
    setPanelMode("form");
  };

  const handleSelectCheckpoint = (chk: MaterialCheckpoint) => {
    setSelectedId(chk.id);
    if (isVideo && chk.stop_time_seconds !== null && chk.stop_time_seconds !== undefined) {
      seekVideoTo(chk.stop_time_seconds, true);
    } else if (!isVideo && chk.section_index) {
      setCurrentPageIndex(chk.section_index);
    }
  };

  const handleMoveSectionCheckpoint = async (checkpointId: string, newSectionIndex: number) => {
    const previous = checkpoints;
    setCheckpoints((prev) =>
      prev.map((c) => (c.id === checkpointId ? { ...c, section_index: newSectionIndex } : c))
    );
    setSelectedId(checkpointId);
    setCurrentPageIndex(newSectionIndex);
    if (editingId === checkpointId) {
      setSectionIndex(newSectionIndex);
    }

    try {
      await learningService.updateCheckpoint(courseId, checkpointId, {
        section_index: newSectionIndex,
      });
      showToast("success", `Đã chuyển câu hỏi sang Trang/Slide ${newSectionIndex}`);
    } catch (err) {
      setCheckpoints(previous);
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể dời vị trí câu hỏi."
      );
    }
  };

  const handleEdit = (chk: MaterialCheckpoint) => {
    setSelectedId(chk.id);
    setEditingId(chk.id);
    setQuestionText(chk.question_text);
    setStopTimeSeconds(chk.stop_time_seconds ?? 0);
    setSectionIndex(chk.section_index ?? 1);
    setOptA(chk.options?.A || "");
    setOptB(chk.options?.B || "");
    setOptC(chk.options?.C || "");
    setOptD(chk.options?.D || "");
    setCorrectOption(chk.correct_option || "A");
    setBloomLevel(chk.bloom_level || "UNDERSTAND");
    setSourceCitation(chk.source_citation || "");
    setLoId(chk.lo_id || material?.lo_id || "");
    setTimeLimitSeconds(chk.time_limit_seconds ?? 10);
    setRewindSeconds(chk.rewind_seconds ?? 15);
    setIsBlocking(chk.is_blocking);
    setPanelMode("form");

    if (isVideo && chk.stop_time_seconds !== null && chk.stop_time_seconds !== undefined) {
      seekVideoTo(chk.stop_time_seconds, true);
    }
  };

  const handleMoveCheckpoint = async (checkpointId: string, newSeconds: number) => {
    const previous = checkpoints;
    // Optimistic update so pin stays crisp at new position
    setCheckpoints((prev) =>
      prev.map((c) => (c.id === checkpointId ? { ...c, stop_time_seconds: newSeconds } : c))
    );
    setSelectedId(checkpointId);
    if (editingId === checkpointId) {
      setStopTimeSeconds(newSeconds);
    }

    try {
      await learningService.updateCheckpoint(courseId, checkpointId, {
        stop_time_seconds: newSeconds,
      });
      showToast("success", `Đã dời mốc câu hỏi đến ${formatTimecode(newSeconds)}`);
    } catch (err) {
      setCheckpoints(previous);
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể cập nhật vị trí mốc."
      );
    }
  };

  const handleDelete = async (checkpointId: string) => {
    try {
      await learningService.deleteCheckpoint(courseId, checkpointId);
      showToast("success", "Đã xóa điểm dừng kiểm tra.");
      if (editingId === checkpointId) {
        resetForm(0);
        setPanelMode("list");
      }
      if (selectedId === checkpointId) {
        setSelectedId(null);
      }
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
        bloom_level: bloomLevel,
        source_citation: sourceCitation.trim() || null,
        lo_id: loId || null,
        time_limit_seconds: timeLimitSeconds,
        rewind_seconds: isVideo ? rewindSeconds : 0,
        is_blocking: isBlocking,
      };

      if (editingId) {
        const updated = await learningService.updateCheckpoint(courseId, editingId, payload);
        showToast("success", "Đã cập nhật điểm dừng kiểm tra.");
        setSelectedId(updated.id);
      } else {
        const created = await learningService.createCheckpoint(courseId, material.id, payload);
        showToast("success", "Đã thêm điểm dừng kiểm tra mới.");
        setSelectedId(created.id);
      }
      resetForm(0);
      setPanelMode("list");
      await loadCheckpoints();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể lưu điểm dừng.");
    } finally {
      setSaving(false);
    }
  };

  const handleSuggestCurrentPage = async () => {
    if (!material) return;
    setSuggestingPage(true);
    try {
      const suggestion = await learningService.suggestPageCheckpoint(
        courseId,
        material.id,
        sectionIndex,
        {
          bloom_level: bloomLevel,
          lo_id: loId || null,
        }
      );
      setQuestionText(suggestion.question_text);
      setOptA(suggestion.options?.A || "");
      setOptB(suggestion.options?.B || "");
      setOptC(suggestion.options?.C || "");
      setOptD(suggestion.options?.D || "");
      setCorrectOption(suggestion.correct_option || "A");
      setSourceCitation(`${suggestion.citation}: "${suggestion.evidence_quote}"`);
      showToast("success", `Đã gợi ý câu hỏi từ Trang/Slide ${sectionIndex}!`);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể gợi ý câu hỏi cho trang này."
      );
    } finally {
      setSuggestingPage(false);
    }
  };

  const handleOpenAiDistribute = () => {
    if (!material) return;
    setPanelMode("ai_distribute");
    setAiLoId(material.lo_id || "");
    if (sections.length > 0 || scanError) return;

    setLoadingSections(true);
    setScanError(null);
    learningService
      .getMaterialSections(courseId, material.id)
      .then((res) => {
        setSections(res.sections);
        if (res.sections.length > 0) {
          setSelectedSectionIds(res.sections.map((s) => s.section_id));
        }
      })
      .catch((err) => {
        setScanError(
          err instanceof ApiError
            ? err.message
            : "Không thể bóc tách cấu trúc chương mục tài liệu."
        );
      })
      .finally(() => setLoadingSections(false));
  };

  const handleGenerateBatch = async () => {
    if (!material) return;
    if (selectedSectionIds.length === 0) {
      showToast("warning", "Vui lòng tích chọn ít nhất một phân đoạn.");
      return;
    }
    const totalCount = bloomDist.REMEMBER + bloomDist.UNDERSTAND + bloomDist.APPLY;
    if (totalCount < 1 || totalCount > 10) {
      showToast("warning", "Tổng số câu hỏi theo ma trận Bloom phải từ 1 đến 10.");
      return;
    }
    const selectedWords = sections
      .filter((s) => selectedSectionIds.includes(s.section_id))
      .reduce((acc, s) => acc + s.word_count, 0);
    if (selectedWords < 100) {
      showToast(
        "warning",
        "Mục được chọn quá ít nội dung thông tin (dưới 100 từ). Vui lòng chọn thêm phân đoạn."
      );
      return;
    }

    setGeneratingAi(true);
    setAiSuggestions([]);
    try {
      const res = await learningService.generateCheckpointSuggestions(
        courseId,
        material.id,
        {
          section_ids: selectedSectionIds,
          bloom_level: "UNDERSTAND",
          bloom_distribution: bloomDist,
          num_questions: totalCount,
          lo_id: aiLoId || null,
        }
      );
      setAiSuggestions(res.suggestions);
      if (res.suggestions.length === 0) {
        showToast("warning", "AI chưa tạo được câu hỏi có bằng chứng trích dẫn khớp. Vui lòng thử lại.");
      }
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Lỗi khi sinh câu hỏi AI.");
    } finally {
      setGeneratingAi(false);
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
    lo_id: s.lo_id || (aiLoId ? aiLoId : null),
    is_blocking: true,
    time_limit_seconds: 15,
    rewind_seconds: 0,
  });

  const handleApproveSuggestion = async (s: CheckpointSuggestion) => {
    if (!material) return;
    setSavingBatch(true);
    try {
      await learningService.batchCreateCheckpoints(courseId, material.id, [
        toCheckpointPayload(s),
      ]);
      setAiSuggestions((prev) => prev.filter((item) => item.temp_id !== s.temp_id));
      await loadCheckpoints();
      showToast("success", "Đã thêm thành công câu hỏi vào bài học!");
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể lưu câu hỏi.");
    } finally {
      setSavingBatch(false);
    }
  };

  const handleApproveAllSuggestions = async () => {
    if (!material || aiSuggestions.length === 0) return;
    setSavingBatch(true);
    try {
      const res = await learningService.batchCreateCheckpoints(
        courseId,
        material.id,
        aiSuggestions.map(toCheckpointPayload)
      );
      setAiSuggestions([]);
      await loadCheckpoints();
      setPanelMode("list");
      showToast("success", `Đã thêm thành công ${res.created_count} câu hỏi vào bài học!`);
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể lưu danh sách câu hỏi.");
    } finally {
      setSavingBatch(false);
    }
  };

  const renderForm = () => (
    <form onSubmit={handleSubmit} className="flex h-full flex-col justify-between gap-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-mm-border pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                resetForm(0);
                setPanelMode("list");
              }}
              className="inline-flex items-center gap-1 rounded-md border border-mm-border bg-mm-bg px-2.5 py-1 text-xs font-medium text-mm-heading hover:bg-mm-surface-alt"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Danh sách</span>
            </button>
            <h4 className="text-sm font-bold text-mm-heading">
              {editingId ? "Cập nhật câu hỏi" : "Thêm câu hỏi mới"}
            </h4>
          </div>
        </div>

        {/* Grid position / timer settings: Only relevant for Video */}
        {isVideo ? (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-mm-heading">
                Thời điểm dừng (giây)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={duration > 0 ? Math.floor(duration) : undefined}
                  value={stopTimeSeconds}
                  onChange={(e) => {
                    const val = Math.max(0, Number(e.target.value));
                    setStopTimeSeconds(val);
                    seekVideoTo(val, true);
                  }}
                  className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-2 font-mono text-sm font-semibold text-mm-heading focus:border-mm-brand focus:outline-none"
                />
                <span className="shrink-0 rounded-md bg-amber-500/15 px-2.5 py-2 font-mono text-xs font-bold text-amber-600">
                  {formatTimecode(stopTimeSeconds)}
                </span>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold text-mm-heading">
                Thời gian trả lời (Video đếm ngược)
              </label>
              <select
                value={timeLimitSeconds}
                onChange={(e) => setTimeLimitSeconds(Number(e.target.value))}
                className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-2 text-sm text-mm-heading focus:border-mm-brand focus:outline-none"
              >
                <option value={10}>10 giây (Mặc định)</option>
                <option value={15}>15 giây</option>
                <option value={20}>20 giây</option>
                <option value={30}>30 giây</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-mm-border bg-mm-bg/60 px-3.5 py-2">
              <span className="text-xs text-mm-text-muted">Vị trí chèn câu hỏi:</span>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-500/15 px-2.5 py-1 font-mono text-xs font-bold text-amber-700 dark:text-amber-400">
                  {material?.material_type === "SLIDE"
                    ? `Slide ${sectionIndex}`
                    : material?.material_type === "PDF"
                    ? `Trang ${sectionIndex}`
                    : `Mục ${sectionIndex}`}
                </span>
                {supportsAiDoc && (
                  <button
                    type="button"
                    disabled={suggestingPage}
                    onClick={handleSuggestCurrentPage}
                    aria-label={`AI gợi ý câu hỏi cho Trang ${sectionIndex}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-mm-blue-primary/30 bg-mm-blue-light/40 px-2.5 py-1 text-xs font-semibold text-mm-blue-active transition-all duration-150 hover:bg-mm-blue-light/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mm-blue-primary disabled:opacity-50"
                  >
                    {suggestingPage ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    <span>{suggestingPage ? "Đang gợi ý..." : "AI gợi ý trang này"}</span>
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="checkpoint-bloom-select"
                  className="mb-1 block text-xs font-semibold text-mm-heading"
                >
                  Mức độ nhận thức (Bloom)
                </label>
                <select
                  id="checkpoint-bloom-select"
                  value={bloomLevel}
                  onChange={(e) =>
                    setBloomLevel(e.target.value as "REMEMBER" | "UNDERSTAND" | "APPLY")
                  }
                  className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-2 text-xs font-medium text-mm-heading transition-colors focus:border-mm-blue-primary focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20"
                >
                  <option value="REMEMBER">Nhận biết (Định nghĩa, khái niệm)</option>
                  <option value="UNDERSTAND">Thông hiểu (Nguyên lý, so sánh)</option>
                  <option value="APPLY">Vận dụng (Tình huống thực tế)</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="checkpoint-lo-select"
                  className="mb-1 block text-xs font-semibold text-mm-heading"
                >
                  Chuẩn đầu ra (LO)
                </label>
                <select
                  id="checkpoint-lo-select"
                  value={loId}
                  onChange={(e) => setLoId(e.target.value)}
                  className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-2 text-xs font-medium text-mm-heading transition-colors focus:border-mm-blue-primary focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20"
                >
                  <option value="">-- Không gắn LO --</option>
                  {availableLos.map((lo) => (
                    <option key={lo.id} value={lo.id}>
                      {lo.code} - {lo.description}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label
                htmlFor="checkpoint-citation-input"
                className="mb-1 block text-xs font-semibold text-mm-heading"
              >
                Trích dẫn nguồn (tùy chọn)
              </label>
              <input
                id="checkpoint-citation-input"
                type="text"
                value={sourceCitation}
                onChange={(e) => setSourceCitation(e.target.value)}
                placeholder={`VD: Trích từ Trang ${sectionIndex}, Đoạn 1...`}
                className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-1.5 text-xs text-mm-text transition-colors focus:border-mm-blue-primary focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20"
              />
            </div>
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-xs font-semibold text-mm-heading">
            Nội dung câu hỏi
          </label>
          <textarea
            rows={3}
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="Nhập câu hỏi kiểm tra nhanh nhận thức của sinh viên..."
            className="w-full rounded-lg border border-mm-border bg-mm-surface px-3 py-2 text-sm text-mm-heading focus:border-mm-brand focus:outline-none"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-semibold text-mm-heading">
            Các phương án (Chọn nút tròn bên trái để đặt đáp án đúng)
          </label>
          {[
            { key: "A", val: optA, set: setOptA },
            { key: "B", val: optB, set: setOptB },
            { key: "C", val: optC, set: setOptC },
            { key: "D", val: optD, set: setOptD },
          ].map((item) => {
            const isCorrect = correctOption === item.key;
            return (
              <div
                key={item.key}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-1.5 transition-colors ${
                  isCorrect
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-mm-border bg-mm-surface"
                }`}
              >
                <input
                  type="radio"
                  name="correctOption"
                  checked={isCorrect}
                  onChange={() => setCorrectOption(item.key)}
                  className="h-4 w-4 accent-emerald-600"
                  title={`Chọn ${item.key} là đáp án đúng`}
                />
                <span
                  className={`w-5 text-xs font-bold ${
                    isCorrect ? "text-emerald-600" : "text-mm-heading"
                  }`}
                >
                  {item.key}.
                </span>
                <input
                  type="text"
                  value={item.val}
                  onChange={(e) => item.set(e.target.value)}
                  placeholder={`Nhập nội dung phương án ${item.key}`}
                  className="flex-1 bg-transparent py-1 text-xs text-mm-heading focus:outline-none"
                />
                {isCorrect && <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />}
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-mm-border bg-mm-bg p-3">
          <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-mm-heading">
            <input
              type="checkbox"
              checked={isBlocking}
              onChange={(e) => setIsBlocking(e.target.checked)}
              className="h-4 w-4 rounded accent-mm-brand"
            />
            <span>Bắt buộc vượt qua mới được mở khóa bài sau</span>
          </label>

          {isVideo && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-mm-heading">
              <span>Tua lùi khi sai:</span>
              <input
                type="number"
                min={0}
                max={60}
                value={rewindSeconds}
                onChange={(e) => setRewindSeconds(Math.max(0, Number(e.target.value)))}
                className="w-14 rounded-md border border-mm-border bg-mm-surface px-2 py-1 text-center font-mono text-xs text-mm-heading"
              />
              <span className="text-mm-text-muted">giây</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-mm-border pt-3">
        <MmButton
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            resetForm(0);
            setPanelMode("list");
          }}
        >
          Hủy
        </MmButton>
        <MmButton type="submit" variant="primary" size="sm" disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          <span>{editingId ? "Lưu thay đổi" : "Lưu câu hỏi"}</span>
        </MmButton>
      </div>
    </form>
  );

  const renderAiDistribute = () => {
    const totalRequested = bloomDist.REMEMBER + bloomDist.UNDERSTAND + bloomDist.APPLY;
    const selectedWords = sections
      .filter((s) => selectedSectionIds.includes(s.section_id))
      .reduce((acc, s) => acc + s.word_count, 0);

    return (
      <div className="flex h-full flex-col gap-3">
        <div className="flex items-center justify-between border-b border-mm-border pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPanelMode("list")}
              aria-label="Quay lại danh sách điểm dừng"
              className="inline-flex items-center gap-1 rounded-md border border-mm-border bg-mm-bg px-2.5 py-1 text-xs font-medium text-mm-heading transition-colors hover:bg-mm-btn-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mm-blue-primary"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Danh sách</span>
            </button>
            <h4 className="flex items-center gap-1.5 text-sm font-bold text-mm-heading">
              <Sparkles className="h-4 w-4 text-mm-blue-primary" />
              <span>Rải câu hỏi AI theo Ma trận Bloom</span>
            </h4>
          </div>
        </div>

        {loadingSections ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-xs text-mm-text-muted">
            <Loader2 className="h-6 w-6 animate-spin text-mm-blue-primary" />
            <span>Đang bóc tách phân đoạn tài liệu...</span>
          </div>
        ) : scanError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-mm-border bg-mm-warning-bg/50 p-6 text-center">
            <AlertTriangle className="h-7 w-7 text-mm-warning" />
            <p className="text-xs font-medium text-mm-heading">{scanError}</p>
            <MmButton variant="secondary" size="sm" onClick={() => setPanelMode("list")}>
              Quay lại
            </MmButton>
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {/* Detected Sections */}
            <div className="space-y-1.5 rounded-xl border border-mm-border bg-mm-bg p-3">
              <div className="flex items-center justify-between text-xs font-bold text-mm-heading">
                <span className="inline-flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5 text-mm-blue-primary" />
                  <span>Chọn phân đoạn ({selectedSectionIds.length}/{sections.length})</span>
                </span>
                <span className="font-normal text-mm-text-muted">{selectedWords} từ</span>
              </div>
              <div className="max-h-36 space-y-1.5 overflow-y-auto pr-1">
                {sections.map((sec) => {
                  const checked = selectedSectionIds.includes(sec.section_id);
                  return (
                    <label
                      key={sec.section_id}
                      className={`flex cursor-pointer items-start gap-2 rounded-lg border p-2 text-xs transition-all duration-150 ${
                        checked
                          ? "border-mm-blue-primary bg-mm-blue-light/25"
                          : "border-mm-border bg-mm-surface hover:border-mm-blue-400"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setSelectedSectionIds((prev) =>
                            prev.includes(sec.section_id)
                              ? prev.filter((x) => x !== sec.section_id)
                              : [...prev, sec.section_id]
                          )
                        }
                        className="mt-0.5 h-3.5 w-3.5 rounded border-mm-border text-mm-blue-primary focus:ring-mm-blue-primary"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2 font-semibold text-mm-heading">
                          <span className="truncate">{sec.title}</span>
                          <span className="shrink-0 text-[10px] text-mm-text-muted">
                            {sec.word_count} từ
                          </span>
                        </div>
                        {sec.summary && (
                          <p className="mt-0.5 line-clamp-2 text-[11px] text-mm-text-secondary">
                            {sec.summary}
                          </p>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Bloom Distribution Matrix */}
            <div className="space-y-2.5 rounded-xl border border-mm-border bg-mm-surface p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-mm-heading">
                  Ma trận tỉ lệ Bloom (Tổng: {totalRequested} câu)
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg border border-mm-border bg-mm-bg p-2">
                  <label htmlFor="dist-remember" className="block text-[11px] font-semibold text-mm-text-secondary">
                    Nhận biết
                  </label>
                  <input
                    id="dist-remember"
                    type="number"
                    min={0}
                    max={10}
                    value={bloomDist.REMEMBER}
                    onChange={(e) =>
                      setBloomDist((prev) => ({
                        ...prev,
                        REMEMBER: Math.max(0, Math.min(10, Number(e.target.value))),
                      }))
                    }
                    className="mt-1 w-full rounded border border-mm-border bg-mm-surface px-2 py-1 text-center font-mono text-xs font-bold text-mm-heading focus:border-mm-blue-primary focus:outline-none"
                  />
                </div>
                <div className="rounded-lg border border-mm-border bg-mm-bg p-2">
                  <label htmlFor="dist-understand" className="block text-[11px] font-semibold text-mm-blue-active">
                    Thông hiểu
                  </label>
                  <input
                    id="dist-understand"
                    type="number"
                    min={0}
                    max={10}
                    value={bloomDist.UNDERSTAND}
                    onChange={(e) =>
                      setBloomDist((prev) => ({
                        ...prev,
                        UNDERSTAND: Math.max(0, Math.min(10, Number(e.target.value))),
                      }))
                    }
                    className="mt-1 w-full rounded border border-mm-border bg-mm-surface px-2 py-1 text-center font-mono text-xs font-bold text-mm-heading focus:border-mm-blue-primary focus:outline-none"
                  />
                </div>
                <div className="rounded-lg border border-mm-border bg-mm-bg p-2">
                  <label htmlFor="dist-apply" className="block text-[11px] font-semibold text-mm-blue-primary">
                    Vận dụng
                  </label>
                  <input
                    id="dist-apply"
                    type="number"
                    min={0}
                    max={10}
                    value={bloomDist.APPLY}
                    onChange={(e) =>
                      setBloomDist((prev) => ({
                        ...prev,
                        APPLY: Math.max(0, Math.min(10, Number(e.target.value))),
                      }))
                    }
                    className="mt-1 w-full rounded border border-mm-border bg-mm-surface px-2 py-1 text-center font-mono text-xs font-bold text-mm-heading focus:border-mm-blue-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <select
                  aria-label="Chọn chuẩn đầu ra cho câu hỏi AI"
                  value={aiLoId}
                  onChange={(e) => setAiLoId(e.target.value)}
                  className="min-w-0 flex-1 rounded-lg border border-mm-border bg-mm-surface px-2.5 py-1.5 text-xs text-mm-heading focus:border-mm-blue-primary focus:outline-none"
                >
                  <option value="">-- Không gắn LO --</option>
                  {availableLos.map((lo) => (
                    <option key={lo.id} value={lo.id}>
                      {lo.code} - {lo.description}
                    </option>
                  ))}
                </select>
                <MmButton
                  type="button"
                  variant="brand"
                  size="sm"
                  disabled={generatingAi || selectedSectionIds.length === 0 || totalRequested < 1}
                  onClick={handleGenerateBatch}
                >
                  {generatingAi ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  <span>{generatingAi ? "Đang tạo..." : "Sinh câu hỏi"}</span>
                </MmButton>
              </div>
            </div>

            {/* AI Suggestions Preview */}
            {aiSuggestions.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-mm-heading">
                    Gợi ý sẵn sàng duyệt ({aiSuggestions.length})
                  </span>
                  <MmButton
                    type="button"
                    variant="brand"
                    size="sm"
                    disabled={savingBatch}
                    onClick={handleApproveAllSuggestions}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Duyệt Tất Cả ({aiSuggestions.length})</span>
                  </MmButton>
                </div>

                {aiSuggestions.map((s) => {
                  const isEditing = editingTempId === s.temp_id;
                  return (
                    <div
                      key={s.temp_id}
                      className="space-y-2 rounded-xl border border-mm-border bg-mm-surface p-3 shadow-sm transition-all duration-150 hover:border-mm-blue-400"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <BloomBadge level={s.bloom_level} />
                          <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] font-bold text-amber-700">
                            Trang {s.citation_page}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setEditingTempId(isEditing ? null : s.temp_id)}
                            className="inline-flex items-center gap-1 rounded border border-mm-border px-2 py-1 text-[11px] font-medium text-mm-heading transition-colors hover:bg-mm-btn-secondary"
                          >
                            <Pencil className="h-3 w-3" />
                            <span>{isEditing ? "Xong" : "Sửa"}</span>
                          </button>
                          <button
                            type="button"
                            disabled={savingBatch}
                            onClick={() => handleApproveSuggestion(s)}
                            className="inline-flex items-center gap-1 rounded bg-mm-blue-primary px-2.5 py-1 text-[11px] font-semibold text-white transition-colors hover:bg-mm-blue-hover disabled:opacity-50"
                          >
                            <Check className="h-3 w-3" />
                            <span>Duyệt</span>
                          </button>
                        </div>
                      </div>

                      {isEditing ? (
                        <textarea
                          value={s.question_text}
                          onChange={(e) =>
                            setAiSuggestions((prev) =>
                              prev.map((item) =>
                                item.temp_id === s.temp_id
                                  ? { ...item, question_text: e.target.value }
                                  : item
                              )
                            )
                          }
                          rows={2}
                          className="w-full rounded border border-mm-blue-primary p-1.5 text-xs text-mm-heading"
                        />
                      ) : (
                        <p className="text-xs font-semibold text-mm-heading">{s.question_text}</p>
                      )}

                      <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                        {(["A", "B", "C", "D"] as const).map((k) => (
                          <div
                            key={k}
                            className={`rounded border px-2 py-1 text-[11px] ${
                              s.correct_option === k
                                ? "border-mm-success bg-mm-success-bg font-semibold text-mm-success"
                                : "border-mm-border bg-mm-bg text-mm-text-secondary"
                            }`}
                          >
                            <strong>{k}.</strong> {s.options[k]}
                          </div>
                        ))}
                      </div>

                      <div className="flex items-start gap-1.5 rounded bg-mm-blue-light/25 px-2 py-1.5 text-[11px] text-mm-blue-deep">
                        <Quote className="mt-0.5 h-3 w-3 shrink-0 text-mm-blue-primary" />
                        <span>
                          <strong>{s.citation}:</strong> <em>"{s.evidence_quote}"</em>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderCheckpointsList = () => (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-mm-border pb-3">
        <div>
          <h4 className="text-sm font-bold text-mm-heading">
            Câu hỏi trong {isVideo ? "Video" : "Tài liệu"} ({sortedCheckpoints.length})
          </h4>
          <p className="text-[11px] text-mm-text-muted">
            {isVideo
              ? "Click vào một câu hỏi để nhảy tới đúng thời điểm dừng"
              : "Click vào câu hỏi để nhảy tới đúng Trang / Slide / Mục"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {supportsAiDoc && (
            <MmButton
              type="button"
              size="sm"
              variant="secondary"
              onClick={handleOpenAiDistribute}
              aria-label="Rải câu hỏi tự động bằng AI theo ma trận Bloom"
            >
              <Sparkles className="h-3.5 w-3.5 text-mm-blue-primary" />
              <span>Rải câu hỏi AI</span>
            </MmButton>
          )}
          {isVideo ? (
            <MmButton type="button" size="sm" variant="primary" onClick={handleOpenAddAtCurrentTime}>
              <Plus className="h-3.5 w-3.5" />
              <span>Tại {formatTimecode(currentTime)}</span>
            </MmButton>
          ) : (
            <MmButton
              type="button"
              size="sm"
              variant="primary"
              onClick={() => handleOpenAddAtSection(currentPageIndex)}
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Tại Mục/Trang {currentPageIndex}</span>
            </MmButton>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-2.5 overflow-y-auto pr-1">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-xs text-mm-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Đang tải danh sách câu hỏi...</span>
          </div>
        ) : sortedCheckpoints.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-mm-border bg-mm-bg p-8 text-center">
            <BookmarkCheck className="mb-2 h-8 w-8 text-mm-text-muted opacity-60" />
            <p className="text-xs font-medium text-mm-heading">
              Chưa có câu hỏi kiểm tra nào.
            </p>
            {isVideo && (
              <p className="mt-1 text-[11px] text-mm-text-muted">
                Hãy kéo thanh thời gian bên trái tới vị trí mong muốn rồi bấm nút{" "}
                <strong>+ Thêm câu hỏi</strong>.
              </p>
            )}
          </div>
        ) : (
          sortedCheckpoints.map((chk, idx) => {
            const isSelected = selectedId === chk.id;
            return (
              <div
                key={chk.id}
                role="button"
                tabIndex={0}
                onClick={() => handleSelectCheckpoint(chk)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectCheckpoint(chk);
                  }
                }}
                className={`group cursor-pointer rounded-xl border p-3.5 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mm-blue-primary ${
                  isSelected
                    ? "border-amber-500 bg-amber-500/10 ring-2 ring-amber-500/40"
                    : "border-mm-border bg-mm-surface hover:border-mm-blue-400 hover:bg-mm-bg"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 font-mono text-[11px] font-bold text-white">
                        {idx + 1}
                      </span>
                      <span className="rounded-md bg-amber-500/20 px-2 py-0.5 font-mono text-xs font-bold text-amber-700 dark:text-amber-400">
                        {isVideo
                          ? formatTimecode(chk.stop_time_seconds)
                          : `Mục ${chk.section_index ?? 1}`}
                      </span>
                      {chk.bloom_level && <BloomBadge level={chk.bloom_level} />}
                      <span
                        className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                          chk.is_blocking
                            ? "bg-rose-500/15 text-rose-600"
                            : "bg-sky-500/15 text-sky-600"
                        }`}
                      >
                        {chk.is_blocking ? "Bắt buộc" : "Tùy chọn"}
                      </span>
                      <span className="rounded-md bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                        Đáp án: {chk.correct_option}
                      </span>
                    </div>

                    <p className="mt-2 text-sm font-medium leading-snug text-mm-heading">
                      {chk.question_text}
                    </p>
                    {chk.source_citation && (
                      <p className="mt-1.5 flex items-start gap-1 text-[11px] text-mm-text-secondary">
                        <Quote className="mt-0.5 h-3 w-3 shrink-0 text-mm-blue-primary" />
                        <span className="line-clamp-2 italic">{chk.source_citation}</span>
                      </p>
                    )}
                  </div>

                  <div
                    className="flex shrink-0 items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={() => handleEdit(chk)}
                      className="rounded-lg border border-mm-border bg-mm-surface p-1.5 text-mm-text-muted transition-colors hover:border-mm-brand hover:text-mm-brand"
                      title="Chỉnh sửa câu hỏi"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(chk.id)}
                      className="rounded-lg border border-mm-border bg-mm-surface p-1.5 text-mm-error transition-colors hover:border-mm-error hover:bg-mm-error-bg"
                      title="Xóa câu hỏi"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="checkpoint-studio-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-2 sm:p-3"
    >
      <div className="flex h-[94vh] w-[96vw] max-w-7xl flex-col overflow-hidden rounded-2xl border border-mm-border bg-mm-surface shadow-2xl lg:h-[90vh]">
        {/* Crisp Solid Header */}
        <div className="flex items-center justify-between border-b border-mm-border bg-mm-surface px-4 py-3 sm:px-6 sm:py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/15 text-amber-600">
              <BookmarkCheck className="h-5 w-5" />
            </div>
            <div>
              <h3 id="checkpoint-studio-title" className="font-mm-mid text-base font-bold text-mm-heading">
                {isVideo
                  ? "Video Checkpoint Studio (Kéo thả điểm dừng)"
                  : `Biên tập Câu hỏi Tài liệu (${material.material_type})`}
              </h3>
              <p className="text-xs text-mm-text-muted">{material.title}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-mm-border p-1.5 text-mm-text-muted transition-colors hover:bg-mm-surface-alt hover:text-mm-heading"
            aria-label="Đóng trình biên tập"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Main Studio Body */}
        {isVideo ? (
          <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-12">
            {/* Left 7 Cols: Dark Video Studio Stage + CapCut Timeline */}
            <div className="flex flex-col justify-between gap-3 overflow-y-auto bg-slate-950 p-5 lg:col-span-7">
              {/* Video Player Viewport */}
              <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-slate-800 bg-black shadow-lg">
                {videoUrl ? (
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    preload="metadata"
                    onClick={togglePlayPause}
                    onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
                    onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => setIsPlaying(false)}
                    className="h-full w-full cursor-pointer object-contain"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-slate-400">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Đang tải nguồn video...
                  </div>
                )}
              </div>

              {/* Studio Transport Controls + Quick Add Button */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={togglePlayPause}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-white text-slate-950 shadow transition-transform hover:scale-105"
                    title={isPlaying ? "Tạm dừng" : "Phát video"}
                  >
                    {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </button>

                  <div className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-950 p-1">
                    <button
                      type="button"
                      onClick={() => seekVideoTo(currentTime - 5)}
                      className="inline-flex items-center gap-0.5 rounded px-2 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                      title="Lùi 5 giây"
                    >
                      <RotateCcw className="h-3 w-3" />
                      <span>5s</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => seekVideoTo(currentTime - 1)}
                      className="rounded px-2 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                      title="Lùi 1 giây"
                    >
                      -1s
                    </button>
                    <button
                      type="button"
                      onClick={() => seekVideoTo(currentTime + 1)}
                      className="rounded px-2 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                      title="Tiến 1 giây"
                    >
                      +1s
                    </button>
                    <button
                      type="button"
                      onClick={() => seekVideoTo(currentTime + 5)}
                      className="inline-flex items-center gap-0.5 rounded px-2 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                      title="Tiến 5 giây"
                    >
                      <span>5s</span>
                      <RotateCw className="h-3 w-3" />
                    </button>
                  </div>

                  <span className="ml-2 font-mono text-sm font-bold text-white">
                    {formatTimecode(currentTime)}{" "}
                    <span className="font-normal text-slate-400">/ {formatTimecode(duration)}</span>
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleOpenAddAtCurrentTime}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3.5 py-2 text-xs font-bold text-slate-950 shadow-md transition-colors hover:bg-amber-400"
                >
                  <Plus className="h-4 w-4" />
                  <span>Thêm câu hỏi tại {formatTimecode(currentTime)}</span>
                </button>
              </div>

              {/* CapCut-style Timeline Track */}
              <VideoTimelineTrack
                duration={duration}
                currentTime={currentTime}
                checkpoints={checkpoints}
                selectedCheckpointId={selectedId}
                onScrubVideo={(sec) => seekVideoTo(sec, true)}
                onSelectCheckpoint={handleSelectCheckpoint}
                onMoveCheckpoint={handleMoveCheckpoint}
              />
            </div>

            {/* Right 5 Cols: High-contrast Question List / Editor Form / AI Distribute */}
            <div className="flex flex-col overflow-y-auto border-t border-mm-border bg-mm-surface p-4 sm:p-5 lg:col-span-5 lg:border-l lg:border-t-0">
              {panelMode === "form"
                ? renderForm()
                : panelMode === "ai_distribute"
                ? renderAiDistribute()
                : renderCheckpointsList()}
            </div>
          </div>
        ) : (
          /* Non-video (PDF / Slide / Document): Unified Interactive Studio */
          <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-12">
            {/* Left 7 Cols: PDF/Slide Filmstrip Stage or Notion Section Stage */}
            <div className="flex flex-col justify-between gap-3 overflow-y-auto bg-mm-bg p-5 lg:col-span-7">
              {structuredLoading ? (
                <div className="flex flex-1 items-center justify-center text-sm text-mm-text-muted">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin text-mm-brand" />
                  Đang phân tích cấu trúc trang / slide tài liệu...
                </div>
              ) : structuredContent &&
                (structuredContent.content_kind === "PDF_PAGES" ||
                  structuredContent.content_kind === "SLIDE_DECK") ? (
                <>
                  <SlidePdfStage
                    courseId={courseId}
                    materialId={material.id}
                    contentKind={structuredContent.content_kind}
                    items={structuredContent.items}
                    currentIndex={currentPageIndex}
                    onChangeIndex={setCurrentPageIndex}
                  />

                  <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-white">
                    <span className="text-xs text-slate-300">
                      Đang xem{" "}
                      <strong className="text-amber-400">
                        {structuredContent.content_kind === "PDF_PAGES" ? "Trang" : "Slide"}{" "}
                        {currentPageIndex}
                      </strong>{" "}
                      / {structuredContent.total_items}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleOpenAddAtSection(currentPageIndex)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3.5 py-2 text-xs font-bold text-slate-950 shadow hover:bg-amber-400"
                    >
                      <Plus className="h-4 w-4" />
                      <span>
                        Thêm câu hỏi vào{" "}
                        {structuredContent.content_kind === "PDF_PAGES" ? "Trang" : "Slide"}{" "}
                        {currentPageIndex}
                      </span>
                    </button>
                  </div>

                  <DocumentFilmstripTrack
                    items={structuredContent.items}
                    currentIndex={currentPageIndex}
                    checkpoints={checkpoints}
                    selectedCheckpointId={selectedId}
                    editable
                    onSelectIndex={setCurrentPageIndex}
                    onSelectCheckpoint={handleSelectCheckpoint}
                    onMoveCheckpoint={handleMoveSectionCheckpoint}
                  />
                </>
              ) : structuredContent && structuredContent.content_kind === "DOC_SECTIONS" ? (
                <DocumentSectionsStage
                  items={structuredContent.items}
                  checkpoints={sortedCheckpoints}
                  editable
                  selectedCheckpointId={selectedId}
                  onAddAtSection={handleOpenAddAtSection}
                  onSelectCheckpoint={handleSelectCheckpoint}
                  onEditCheckpoint={handleEdit}
                  onDeleteCheckpoint={handleDelete}
                />
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center rounded-xl border-2 border-dashed border-mm-border bg-mm-surface p-8 text-center text-xs text-mm-text-muted">
                  <p className="font-medium text-mm-heading">
                    Học liệu chưa có tệp nội dung xem trước (hoặc là liên kết ngoài).
                  </p>
                  <p className="mt-1">
                    Bạn vẫn có thể thêm câu hỏi kiểm tra theo số Mục/Trang ở bảng bên phải.
                  </p>
                </div>
              )}
            </div>

            {/* Right 5 Cols: High-contrast Question List / Editor Form / AI Distribute */}
            <div className="flex flex-col overflow-y-auto border-t border-mm-border bg-mm-surface p-4 sm:p-5 lg:col-span-5 lg:border-l lg:border-t-0">
              {panelMode === "form"
                ? renderForm()
                : panelMode === "ai_distribute"
                ? renderAiDistribute()
                : renderCheckpointsList()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
