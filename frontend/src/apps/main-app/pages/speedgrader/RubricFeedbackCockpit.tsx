/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  CheckCheck,
  Link2,
  Lock,
  Mic,
  Save,
  Sparkles,
  Square,
  Trash2,
  Volume2,
} from "lucide-react";
import { clsx } from "clsx";

import { gradebookService } from "../../../../services/gradebookService";
import type {
  CriterionProposalItem,
  EvidenceFlag,
  RubricProposalResponse,
  SpeedGraderWorkspaceResponse,
} from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

export interface RubricScoreMap {
  [criterionId: string]: {
    points: number;
    label?: string;
    lo_id?: string | null;
  };
}

interface RubricFeedbackCockpitProps {
  workspace: SpeedGraderWorkspaceResponse;
  aiProposal: RubricProposalResponse | null;
  loadingAi: boolean;
  officialScore: string;
  rubricScores: RubricScoreMap;
  feedbackText: string;
  overrideReason: string;
  voiceFeedbackUrl: string | null;
  draftSavedAt: string | null;
  savingGrade: boolean;
  onRequestAiProposal: () => void;
  onChangeOfficialScore: (val: string) => void;
  onChangeRubricScores: (next: RubricScoreMap, computedTotal: number) => void;
  onChangeFeedback: (val: string) => void;
  onChangeOverrideReason: (val: string) => void;
  onChangeVoiceFeedbackUrl: (url: string | null) => void;
  onHighlightCitation: (ref: string) => void;
  onSaveAndNext: (moveNext: boolean) => void;
}

const FLAG_META: Record<
  EvidenceFlag,
  { label: string; badgeClass: string; desc: string }
> = {
  SUFFICIENT: {
    label: "SUFFICIENT — Đủ bằng chứng",
    badgeClass: "border-[#a7f3d0] bg-[#ecfdf5] text-[#047857]",
    desc: "Bài nộp và biên bản Viva nhất quán, đủ căn cứ đề xuất điểm tham khảo.",
  },
  INSUFFICIENT: {
    label: "INSUFFICIENT — Thiếu bằng chứng",
    badgeClass: "border-amber-200 bg-amber-50 text-amber-800",
    desc: "Thiếu dữ liệu Viva hoặc minh chứng bài nộp chưa đầy đủ. Giảng viên cần xem kỹ.",
  },
  CONFLICTING: {
    label: "CONFLICTING — Mâu thuẫn nghiêm trọng",
    badgeClass: "border-rose-200 bg-rose-50 text-rose-700",
    desc: "Phát hiện mâu thuẫn giữa bài nộp, câu trả lời Viva hoặc nhật ký vi phạm liêm chính.",
  },
  HUMAN_REVIEW: {
    label: "HUMAN_REVIEW — Chấm thủ công",
    badgeClass: "border-slate-300 bg-slate-100 text-slate-700",
    desc: "AI không đưa ra đề xuất tự động (E-12). Giảng viên trực tiếp chấm điểm theo Rubric.",
  },
};

const MAX_VOICE_SECONDS = 120;

export const RubricFeedbackCockpit: React.FC<RubricFeedbackCockpitProps> = ({
  workspace,
  aiProposal,
  loadingAi,
  officialScore,
  rubricScores,
  feedbackText,
  overrideReason,
  voiceFeedbackUrl,
  draftSavedAt,
  savingGrade,
  onRequestAiProposal,
  onChangeOfficialScore,
  onChangeRubricScores,
  onChangeFeedback,
  onChangeOverrideReason,
  onChangeVoiceFeedbackUrl,
  onHighlightCitation,
  onSaveAndNext,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [uploadingVoice, setUploadingVoice] = useState(false);
  const [audioObjectUrl, setAudioObjectUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<number | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const isLocked = workspace.is_gradebook_locked;

  // Fetch authenticated audio blob URL whenever voiceFeedbackUrl changes
  useEffect(() => {
    let active = true;
    let createdUrl: string | null = null;

    if (!voiceFeedbackUrl) {
      setAudioObjectUrl(null);
      return;
    }

    gradebookService
      .fetchVoiceFeedbackObjectUrl(voiceFeedbackUrl)
      .then((objUrl) => {
        if (active) {
          createdUrl = objUrl;
          setAudioObjectUrl(objUrl);
        } else {
          URL.revokeObjectURL(objUrl);
        }
      })
      .catch(() => {
        if (active) setAudioObjectUrl(null);
      });

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [voiceFeedbackUrl]);

  // Cleanup recorder on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (timerRef.current) window.clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const parsedOfficial = Number.parseFloat(officialScore);
  const proposedTotal = aiProposal?.proposed_total_score;
  const requiresOverrideReason =
    !Number.isNaN(parsedOfficial) &&
    typeof proposedTotal === "number" &&
    Math.abs(parsedOfficial - proposedTotal) > 1.5;

  const proposalByCriterion = new Map<string, CriterionProposalItem>();
  (aiProposal?.criteria_proposals ?? []).forEach((item) => {
    proposalByCriterion.set(item.criterion_id, item);
  });

  const handleSelectRating = (
    criterionId: string,
    points: number,
    label: string,
    loId?: string | null
  ) => {
    if (isLocked) return;
    const next: RubricScoreMap = {
      ...rubricScores,
      [criterionId]: { points, label, lo_id: loId ?? null },
    };
    const total = Object.values(next).reduce((acc, item) => acc + (Number(item.points) || 0), 0);
    onChangeRubricScores(next, Math.min(10, Math.round(total * 100) / 100));
  };

  const handleAcceptCriterion = (proposal: CriterionProposalItem) => {
    if (isLocked) return;
    const criterion = workspace.rubric_criteria.find((c) => c.id === proposal.criterion_id);
    handleSelectRating(
      proposal.criterion_id,
      proposal.proposed_points,
      proposal.rating_level_label,
      criterion?.lo_id
    );
  };

  const handleAcceptAllProposals = () => {
    if (isLocked || !aiProposal || aiProposal.criteria_proposals.length === 0) return;
    const next: RubricScoreMap = { ...rubricScores };
    for (const prop of aiProposal.criteria_proposals) {
      const criterion = workspace.rubric_criteria.find((c) => c.id === prop.criterion_id);
      next[prop.criterion_id] = {
        points: prop.proposed_points,
        label: prop.rating_level_label,
        lo_id: criterion?.lo_id ?? null,
      };
    }
    const total = Object.values(next).reduce((acc, item) => acc + (Number(item.points) || 0), 0);
    onChangeRubricScores(next, Math.min(10, Math.round(total * 100) / 100));
    toast.success("Đã áp dụng toàn bộ điểm đề xuất AI vào Rubric (bạn vẫn có thể điều chỉnh trước khi lưu).");
  };

  const stopRecording = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const startRecording = async () => {
    if (isLocked) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast.error("Trình duyệt hiện tại không hỗ trợ ghi âm micro.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunksRef.current.push(ev.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        if (!isMountedRef.current) return;
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) return;
        try {
          setUploadingVoice(true);
          const uploaded = await gradebookService.uploadVoiceFeedback(
            blob,
            `voice_${workspace.submission_id.slice(0, 8)}.webm`
          );
          if (!isMountedRef.current) return;
          onChangeVoiceFeedbackUrl(uploaded.voice_feedback_url);
          toast.success("Đã tải lên nhận xét giọng nói thành công.");
        } catch (err: unknown) {
          if (!isMountedRef.current) return;
          const code = (err as { code?: string })?.code;
          toast.error(resolveErrorMessage(code, "Không thể tải lên tệp ghi âm."));
        } finally {
          if (isMountedRef.current) {
            setUploadingVoice(false);
          }
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev + 1 >= MAX_VOICE_SECONDS) {
            stopRecording();
            return MAX_VOICE_SECONDS;
          }
          return prev + 1;
        });
      }, 1000);
    } catch {
      toast.error("Không thể truy cập micro. Vui lòng cấp quyền micro cho trình duyệt.");
    }
  };

  const flagMeta = aiProposal ? FLAG_META[aiProposal.evidence_flag] : null;

  return (
    <div className="flex h-full flex-col rounded-2xl border border-[#e5e7eb] bg-white shadow-xs">
      {/* Column 3 Header */}
      <div className="border-b border-[#f3f4f6] p-4 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <h2 className="font-mm-display text-sm font-bold text-mm-dark truncate">
            Cột 3: Bảng điểm Rubric & Phản hồi
          </h2>
          <p className="text-[11px] text-[#6b7280] truncate">
            {workspace.rubric_title || "Chấm điểm trực tiếp (Thang 10)"}
          </p>
        </div>
        <span
          className={clsx(
            "rounded-full px-2.5 py-0.5 font-mm-mono text-[10px] font-semibold shrink-0",
            workspace.grading_status === "INSTRUCTOR_REVIEWED"
              ? "bg-[#ecfdf5] text-[#047857]"
              : workspace.grading_status === "AI_PROPOSED"
                ? "bg-[#eff6ff] text-[#1e40af]"
                : "bg-gray-100 text-[#4b5563]"
          )}
        >
          {workspace.grading_status}
        </span>
      </div>

      {/* Column 3 Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLocked && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-center gap-2">
            <Lock className="h-4 w-4 shrink-0" />
            <span>
              Sổ điểm học phần đã khóa vĩnh viễn (E-14). Không thể chỉnh sửa điểm số hoặc nhận xét.
            </span>
          </div>
        )}

        {/* AI Cross-Evidence Assistant Card (T2-I-M5-03) */}
        <div className="rounded-xl border border-[#dbeafe] bg-[#eff6ff]/50 p-3.5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1e3a8a]">
              <Sparkles className="h-3.5 w-3.5 text-mm-blue-primary" />
              Trợ lý AI Đối soát Rubric (BR-07)
            </span>
            <div className="flex items-center gap-1.5">
              <MmButton
                variant="secondary"
                size="sm"
                onClick={onRequestAiProposal}
                disabled={loadingAi || isLocked}
              >
                {loadingAi ? "Đang phân tích..." : aiProposal ? "Phân tích lại" : "Yêu cầu AI đề xuất"}
              </MmButton>
              {aiProposal && aiProposal.criteria_proposals.length > 0 && !isLocked && (
                <MmButton variant="primary" size="sm" onClick={handleAcceptAllProposals}>
                  <CheckCheck className="h-3.5 w-3.5 mr-1" />
                  Chấp nhận tất cả
                </MmButton>
              )}
            </div>
          </div>

          {aiProposal && flagMeta ? (
            <div className="space-y-2 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span
                  className={clsx(
                    "rounded-full border px-2.5 py-0.5 font-mm-mono text-[10px] font-bold",
                    flagMeta.badgeClass
                  )}
                >
                  {flagMeta.label}
                </span>
                {typeof aiProposal.proposed_total_score === "number" && (
                  <span className="font-mm-mono text-xs font-bold text-[#1e3a8a]">
                    AI Đề xuất: {aiProposal.proposed_total_score.toFixed(2)} / 10
                  </span>
                )}
              </div>
              <p className="text-[11px] text-[#374151] leading-relaxed">
                {aiProposal.summary_comment || flagMeta.desc}
              </p>
            </div>
          ) : (
            <p className="text-[11px] text-[#4b5563] leading-relaxed">
              Nhấn <strong>Yêu cầu AI đề xuất</strong> để AI đối soát đồng thời Bản tóm tắt Call-1, biên bản Viva và Rubric kèm trích dẫn cụ thể. AI chỉ gợi ý, Giảng viên là người chốt điểm.
            </p>
          )}
        </div>

        {/* Interactive Rubric Matrix */}
        {workspace.rubric_criteria.length > 0 && (
          <div className="space-y-3">
            {workspace.rubric_criteria.map((criterion) => {
              const selected = rubricScores[criterion.id];
              const aiItem = proposalByCriterion.get(criterion.id);

              return (
                <div
                  key={criterion.id}
                  className="rounded-xl border border-[#e5e7eb] bg-white p-3 space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-mm-dark">{criterion.title}</span>
                        {criterion.competency_code && (
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 font-mm-mono text-[10px] font-semibold text-[#4b5563]">
                            {criterion.competency_code}
                          </span>
                        )}
                      </div>
                      {criterion.description && (
                        <p className="mt-0.5 text-[11px] text-[#6b7280]">{criterion.description}</p>
                      )}
                    </div>
                    <span className="font-mm-mono text-xs font-bold text-mm-blue-primary shrink-0">
                      {selected ? selected.points : 0} / {criterion.max_points}
                    </span>
                  </div>

                  {/* AI Criterion Proposal + Citations */}
                  {aiItem && (
                    <div className="rounded-lg border border-[#dbeafe] bg-[#f8fafc] p-2.5 text-[11px] space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-[#1e40af]">
                          AI gợi ý: {aiItem.proposed_points}/{aiItem.max_points} đ ({aiItem.rating_level_label})
                        </span>
                        {!isLocked && (
                          <button
                            type="button"
                            onClick={() => handleAcceptCriterion(aiItem)}
                            className="inline-flex items-center gap-1 rounded-md bg-white border border-[#bfdbfe] px-2 py-0.5 text-[10px] font-semibold text-[#1e40af] hover:bg-[#eff6ff]"
                          >
                            <Check className="h-3 w-3" />
                            Chấp nhận
                          </button>
                        )}
                      </div>
                      <p className="text-[#374151] leading-relaxed">{aiItem.explanation}</p>
                      {aiItem.citations.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {aiItem.citations.map((cit, idx) => (
                            <button
                              key={`${cit.reference}-${idx}`}
                              type="button"
                              onClick={() => onHighlightCitation(cit.reference)}
                              className="inline-flex items-center gap-1 rounded-full bg-white border border-[#e5e7eb] px-2 py-0.5 text-[10px] font-mm-mono text-mm-blue-primary hover:border-mm-blue-primary"
                              title={cit.excerpt}
                            >
                              <Link2 className="h-2.5 w-2.5" />
                              Xem vị trí: {cit.reference}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Clickable Rating Levels */}
                  {criterion.rating_levels.length > 0 && (
                    <div className="grid grid-cols-2 gap-1.5">
                      {criterion.rating_levels.map((lvl, idx) => {
                        const pts = Number(lvl.points ?? 0);
                        const label = lvl.label || lvl.level || `Mức ${idx + 1}`;
                        const active =
                          selected !== undefined && Math.abs(selected.points - pts) < 0.001;
                        return (
                          <button
                            key={`${criterion.id}-${idx}`}
                            type="button"
                            disabled={isLocked}
                            onClick={() =>
                              handleSelectRating(criterion.id, pts, label, criterion.lo_id)
                            }
                            className={clsx(
                              "rounded-lg border p-2 text-left transition-all text-[11px]",
                              active
                                ? "border-mm-blue-primary bg-[#eff6ff] text-[#1e3a8a] font-semibold"
                                : "border-[#e5e7eb] bg-[#fafafa] text-[#374151] hover:border-gray-300",
                              isLocked && "opacity-60 cursor-not-allowed"
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <span className="truncate">{label}</span>
                              <span className="font-mm-mono font-bold">{pts}đ</span>
                            </div>
                            {lvl.description && (
                              <p className="mt-0.5 text-[10px] text-[#6b7280] line-clamp-2 font-normal">
                                {lvl.description}
                              </p>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Official Score Input + Override Reason (E-GB-07) */}
        <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3.5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <label
              htmlFor="sg-official-score"
              className="text-xs font-bold text-mm-dark"
            >
              Điểm chính thức (0.00 - 10.00)
            </label>
            <input
              id="sg-official-score"
              type="number"
              min={0}
              max={10}
              step={0.1}
              disabled={isLocked}
              value={officialScore}
              onChange={(e) => onChangeOfficialScore(e.target.value)}
              className="w-28 rounded-lg border border-[#d1d5db] bg-white px-3 py-1.5 text-right font-mm-mono text-sm font-bold text-mm-dark focus:border-mm-blue-primary focus:outline-none disabled:bg-gray-100"
              placeholder="0.0"
            />
          </div>

          {requiresOverrideReason && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-2.5 space-y-1.5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-900">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                <span>
                  Chênh lệch hơn 1.5 điểm so với AI đề xuất (E-GB-07). Bắt buộc ghi rõ lý do điều chỉnh:
                </span>
              </div>
              <textarea
                rows={2}
                disabled={isLocked}
                value={overrideReason}
                onChange={(e) => onChangeOverrideReason(e.target.value)}
                placeholder="Nhập lý do ghi nhận vào nhật ký kiểm toán điểm..."
                className="w-full rounded-lg border border-amber-300 bg-white p-2 text-xs text-mm-dark focus:border-amber-500 focus:outline-none"
              />
            </div>
          )}
        </div>

        {/* Feedback Textarea + 30s Autosave Indicator (BR-SPEED-01) */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="sg-feedback" className="text-xs font-bold text-mm-dark">
              Nhận xét cho sinh viên
            </label>
            {draftSavedAt && (
              <span className="font-mm-mono text-[10px] text-[#047857]">
                Đã lưu nháp lúc {new Date(draftSavedAt).toLocaleTimeString("vi-VN")}
              </span>
            )}
          </div>
          <textarea
            id="sg-feedback"
            rows={4}
            disabled={isLocked}
            value={feedbackText}
            onChange={(e) => onChangeFeedback(e.target.value)}
            placeholder="Nhập nhận xét chi tiết cho bài làm và phần vấn đáp Viva của sinh viên..."
            className="w-full rounded-xl border border-[#d1d5db] bg-white p-3 text-xs text-mm-dark leading-relaxed focus:border-mm-blue-primary focus:outline-none disabled:bg-gray-50"
          />
        </div>

        {/* Voice Feedback Recorder (<= 120s, Object Storage via Backend Proxy) */}
        <div className="rounded-xl border border-[#e5e7eb] bg-[#fafafa] p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mm-dark">
              <Volume2 className="h-3.5 w-3.5 text-mm-blue-primary" />
              Nhận xét bằng giọng nói (tối đa 120 giây)
            </span>
            {isRecording && (
              <span className="font-mm-mono text-xs font-bold text-rose-600">
                Đang ghi: {recordingSeconds}s / {MAX_VOICE_SECONDS}s
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {!isRecording ? (
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => void startRecording()}
                disabled={isLocked || uploadingVoice}
              >
                <Mic className="h-3.5 w-3.5 mr-1 text-rose-600" />
                {uploadingVoice ? "Đang tải lên..." : "Ghi âm nhận xét"}
              </MmButton>
            ) : (
              <MmButton variant="primary" size="sm" onClick={stopRecording}>
                <Square className="h-3.5 w-3.5 mr-1" />
                Dừng & Lưu ghi âm
              </MmButton>
            )}

            {voiceFeedbackUrl && !isLocked && (
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => onChangeVoiceFeedbackUrl(null)}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1 text-rose-600" />
                Xóa bản ghi
              </MmButton>
            )}
          </div>

          {audioObjectUrl && (
            <audio controls src={audioObjectUrl} className="w-full h-9" />
          )}
        </div>
      </div>

      {/* Column 3 Footer Actions */}
      <div className="border-t border-[#f3f4f6] p-4 flex flex-wrap items-center justify-between gap-2 bg-[#fafafa] rounded-b-2xl">
        <MmButton
          variant="secondary"
          size="sm"
          disabled={isLocked || savingGrade}
          onClick={() => onSaveAndNext(false)}
        >
          <Save className="h-3.5 w-3.5 mr-1.5" />
          {savingGrade ? "Đang lưu..." : "Lưu Điểm"}
        </MmButton>
        <MmButton
          variant="primary"
          size="sm"
          disabled={isLocked || savingGrade}
          onClick={() => onSaveAndNext(true)}
        >
          {savingGrade ? "Đang lưu..." : "Lưu Điểm & Sinh viên Tiếp theo"}
        </MmButton>
      </div>
    </div>
  );
};
