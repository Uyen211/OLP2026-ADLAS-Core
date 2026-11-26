/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  EyeOff,
  Filter,
  Lock,
} from "lucide-react";

import { gradebookService } from "../../../../services/gradebookService";
import type {
  RubricProposalResponse,
  SpeedGraderFilter,
  SpeedGraderSubmissionListResponse,
  SpeedGraderWorkspaceResponse,
} from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";
import {
  RubricFeedbackCockpit,
  type RubricScoreMap,
} from "./RubricFeedbackCockpit";
import { SubmissionArtifactViewer } from "./SubmissionArtifactViewer";
import { VivaEvidenceColumn } from "./VivaEvidenceColumn";

export const SpeedGraderPage: React.FC = () => {
  const { courseId, assignmentId } = useParams<{
    courseId: string;
    assignmentId: string;
  }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [filterMode, setFilterMode] = useState<SpeedGraderFilter>("ALL");
  const [listData, setListData] = useState<SpeedGraderSubmissionListResponse | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);

  const [currentSubId, setCurrentSubId] = useState<string | null>(
    searchParams.get("submissionId")
  );
  const [workspace, setWorkspace] = useState<SpeedGraderWorkspaceResponse | null>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState<boolean>(false);

  // Editable form state in Column 3
  const [aiProposal, setAiProposal] = useState<RubricProposalResponse | null>(null);
  const [loadingAi, setLoadingAi] = useState<boolean>(false);
  const [officialScore, setOfficialScore] = useState<string>("");
  const [rubricScores, setRubricScores] = useState<RubricScoreMap>({});
  const [feedbackText, setFeedbackText] = useState<string>("");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [voiceFeedbackUrl, setVoiceFeedbackUrl] = useState<string | null>(null);
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const [savingGrade, setSavingGrade] = useState<boolean>(false);
  const [isDirty, setIsDirty] = useState<boolean>(false);

  // Citation highlight across Col 1 / Col 2
  const [highlightedRef, setHighlightedRef] = useState<string | null>(null);

  // E-SPEED-02 unsaved changes confirmation modal
  const [pendingNavTarget, setPendingNavTarget] = useState<string | null>(null);

  const latestDraftPayloadRef = useRef<{
    submissionId: string | null;
    isDirty: boolean;
    isLocked: boolean;
    feedbackText: string;
    rubricScores: RubricScoreMap;
  }>({
    submissionId: null,
    isDirty: false,
    isLocked: false,
    feedbackText: "",
    rubricScores: {},
  });

  latestDraftPayloadRef.current = {
    submissionId: workspace?.submission_id ?? null,
    isDirty,
    isLocked: workspace?.is_gradebook_locked ?? false,
    feedbackText,
    rubricScores,
  };

  const loadWorkspace = useCallback(
    async (submissionId: string) => {
      try {
        setLoadingWorkspace(true);
        const ws = await gradebookService.getSpeedGraderWorkspace(submissionId);
        setWorkspace(ws);
        setAiProposal(ws.ai_proposal ?? null);
        setOfficialScore(
          ws.official_score !== null && ws.official_score !== undefined
            ? String(ws.official_score)
            : ""
        );
        setRubricScores(ws.rubric_scores ?? {});
        setFeedbackText(ws.instructor_feedback ?? "");
        setOverrideReason("");
        setVoiceFeedbackUrl(ws.voice_feedback_url ?? null);
        setDraftSavedAt(null);
        setIsDirty(false);
        setHighlightedRef(null);
        setSearchParams({ submissionId }, { replace: true });
      } catch (err: unknown) {
        const code = (err as { code?: string })?.code;
        toast.error(resolveErrorMessage(code, "Không thể tải không gian chấm điểm SpeedGrader."));
      } finally {
        setLoadingWorkspace(false);
      }
    },
    [setSearchParams]
  );

  const loadList = useCallback(
    async (preferredSubId?: string | null) => {
      if (!assignmentId) return;
      try {
        setLoadingList(true);
        const data = await gradebookService.listSpeedGraderSubmissions(
          assignmentId,
          filterMode
        );
        setListData(data);
        if (data.items.length === 0) {
          setCurrentSubId(null);
          setWorkspace(null);
          return;
        }
        const targetId =
          preferredSubId && data.items.some((it) => it.submission_id === preferredSubId)
            ? preferredSubId
            : data.items[0].submission_id;
        setCurrentSubId(targetId);
        await loadWorkspace(targetId);
      } catch (err: unknown) {
        const code = (err as { code?: string })?.code;
        toast.error(resolveErrorMessage(code, "Không thể tải danh sách bài nộp SpeedGrader."));
      } finally {
        setLoadingList(false);
      }
    },
    [assignmentId, filterMode, loadWorkspace]
  );

  useEffect(() => {
    void loadList(currentSubId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignmentId, filterMode]);

  // BR-SPEED-01: 30-second auto-save draft timer
  useEffect(() => {
    const interval = window.setInterval(() => {
      const snap = latestDraftPayloadRef.current;
      if (!snap.submissionId || !snap.isDirty || snap.isLocked) return;
      gradebookService
        .saveSpeedGraderDraft(snap.submissionId, {
          instructor_feedback: snap.feedbackText,
          rubric_scores: snap.rubricScores,
        })
        .then((res) => {
          setDraftSavedAt(res.saved_at);
        })
        .catch(() => {
          // Silent retry on next 30s tick
        });
    }, 30000);
    return () => window.clearInterval(interval);
  }, []);

  const requestSwitchSubmission = (targetSubId: string) => {
    if (targetSubId === currentSubId) return;
    if (isDirty && !workspace?.is_gradebook_locked) {
      setPendingNavTarget(targetSubId);
      return;
    }
    setCurrentSubId(targetSubId);
    void loadWorkspace(targetSubId);
  };

  const confirmDiscardAndSwitch = () => {
    if (!pendingNavTarget) return;
    const target = pendingNavTarget;
    setPendingNavTarget(null);
    setIsDirty(false);
    setCurrentSubId(target);
    void loadWorkspace(target);
  };

  const handleRequestAiProposal = async () => {
    if (!workspace) return;
    try {
      setLoadingAi(true);
      const proposal = await gradebookService.generateAiRubricProposal(workspace.submission_id);
      setAiProposal(proposal);
      toast.success("AI đã hoàn tất đối soát bằng chứng và đề xuất điểm Rubric.");
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code;
      toast.error(resolveErrorMessage(code, "Không thể chạy AI đề xuất Rubric."));
    } finally {
      setLoadingAi(false);
    }
  };

  const handleSaveAndNext = async (moveNext: boolean) => {
    if (!workspace) return;
    const scoreNum = Number.parseFloat(officialScore);
    if (Number.isNaN(scoreNum) || scoreNum < 0 || scoreNum > 10) {
      toast.error("Điểm chính thức phải nằm trong khoảng từ 0.00 đến 10.00 (E-GB-02).");
      return;
    }
    const proposedTotal = aiProposal?.proposed_total_score;
    if (
      typeof proposedTotal === "number" &&
      Math.abs(scoreNum - proposedTotal) > 1.5 &&
      overrideReason.trim().length < 5
    ) {
      toast.error(
        "Điểm bạn chấm lệch trên 1.5 điểm so với AI đề xuất. Vui lòng nhập lý do điều chỉnh (E-GB-07)."
      );
      return;
    }

    try {
      setSavingGrade(true);
      const updated = await gradebookService.saveSpeedGraderGrade(workspace.submission_id, {
        official_score: scoreNum,
        rubric_scores: rubricScores,
        instructor_feedback: feedbackText,
        voice_feedback_url: voiceFeedbackUrl,
        override_reason: overrideReason.trim() || undefined,
      });
      setWorkspace(updated);
      setIsDirty(false);
      toast.success("Đã lưu điểm chính thức và nhận xét cho sinh viên.");

      // Refresh progress list in background
      if (assignmentId) {
        const refreshed = await gradebookService.listSpeedGraderSubmissions(
          assignmentId,
          filterMode
        );
        setListData(refreshed);

        if (moveNext && refreshed.items.length > 1) {
          const idx = refreshed.items.findIndex(
            (it) => it.submission_id === updated.submission_id
          );
          const nextItem =
            idx >= 0 && idx + 1 < refreshed.items.length
              ? refreshed.items[idx + 1]
              : refreshed.items[0];
          if (nextItem && nextItem.submission_id !== updated.submission_id) {
            setCurrentSubId(nextItem.submission_id);
            await loadWorkspace(nextItem.submission_id);
          }
        }
      }
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code;
      toast.error(resolveErrorMessage(code, "Không thể lưu điểm cho sinh viên."));
    } finally {
      setSavingGrade(false);
    }
  };

  const items = listData?.items ?? [];
  const currentIdx = items.findIndex((it) => it.submission_id === currentSubId);
  const prevItem = currentIdx > 0 ? items[currentIdx - 1] : null;
  const nextItem = currentIdx >= 0 && currentIdx + 1 < items.length ? items[currentIdx + 1] : null;

  return (
    <div className="min-h-screen bg-[#f5f7fb] flex flex-col">
      {/* Top Navigation & Progress Cockpit Bar */}
      <header className="sticky top-0 z-20 border-b border-[#e5e7eb] bg-white px-4 py-3 shadow-xs">
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-3">
          {/* Left: Back & Assignment Info */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => navigate(courseId ? `/courses/${courseId}/gradebook` : "/courses")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] hover:bg-gray-50"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Sổ điểm
            </button>
            <div className="min-w-0">
              <h1 className="font-mm-display text-sm font-bold text-mm-dark truncate">
                SpeedGrader — {listData?.assignment_title || workspace?.assignment_title || "Chấm bài"}
              </h1>
              <div className="flex items-center gap-2 text-[11px] text-[#6b7280]">
                <span>
                  Tiến độ: <strong>{listData?.graded_count ?? 0}</strong> /{" "}
                  <strong>{listData?.total_submissions ?? 0}</strong> bài đã chấm (
                  {listData?.progress_percent ?? 0}%)
                </span>
                {workspace?.is_column_muted && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                    <EyeOff className="h-3 w-3" />
                    Đang ẩn điểm (Muted)
                  </span>
                )}
                {workspace?.is_gradebook_locked && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700">
                    <Lock className="h-3 w-3" />
                    Đã khóa sổ
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right: Filter & Student Switcher */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-lg border border-[#d1d5db] bg-[#f9fafb] px-2.5 py-1 text-xs">
              <Filter className="h-3.5 w-3.5 text-[#6b7280]" />
              <select
                value={filterMode}
                onChange={(e) => setFilterMode(e.target.value as SpeedGraderFilter)}
                className="bg-transparent text-xs font-medium text-mm-dark focus:outline-none"
              >
                <option value="ALL">Tất cả bài nộp</option>
                <option value="NEEDS_GRADING">Chưa chấm / Chờ duyệt</option>
                <option value="GRADED">Đã chấm xong</option>
                <option value="CONFLICTING">Cảnh báo mâu thuẫn (CONFLICTING)</option>
              </select>
            </div>

            <div className="flex items-center gap-1">
              <MmButton
                variant="secondary"
                size="sm"
                disabled={!prevItem}
                onClick={() => prevItem && requestSwitchSubmission(prevItem.submission_id)}
              >
                <ChevronLeft className="h-4 w-4" />
              </MmButton>

              <select
                value={currentSubId ?? ""}
                onChange={(e) => e.target.value && requestSwitchSubmission(e.target.value)}
                className="max-w-[260px] rounded-lg border border-[#d1d5db] bg-white px-3 py-1.5 text-xs font-semibold text-mm-dark focus:border-mm-blue-primary focus:outline-none"
              >
                {items.map((it) => (
                  <option key={it.submission_id} value={it.submission_id}>
                    {it.student_name} ({it.user_code || it.student_email}) —{" "}
                    {it.official_score !== null && it.official_score !== undefined
                      ? `${it.official_score}đ`
                      : "Chưa chấm"}
                  </option>
                ))}
              </select>

              <MmButton
                variant="secondary"
                size="sm"
                disabled={!nextItem}
                onClick={() => nextItem && requestSwitchSubmission(nextItem.submission_id)}
              >
                <ChevronRight className="h-4 w-4" />
              </MmButton>
            </div>
          </div>
        </div>
      </header>

      {/* Main 3-Column Cockpit Body */}
      <main className="mx-auto w-full max-w-[1680px] flex-1 p-4">
        {loadingList || loadingWorkspace ? (
          <div className="flex min-h-[540px] items-center justify-center rounded-2xl border border-[#e5e7eb] bg-white">
            <div className="flex items-center gap-3 text-sm text-[#6b7280]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-mm-blue-primary border-t-transparent" />
              <span>Đang tải dữ liệu không gian chấm điểm 3 cột...</span>
            </div>
          </div>
        ) : !workspace ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-[#e5e7eb] bg-white p-10 text-center space-y-3">
            <p className="text-sm font-semibold text-mm-dark">
              Không tìm thấy bài nộp phù hợp với bộ lọc hiện tại.
            </p>
            <Link
              to={courseId ? `/courses/${courseId}/gradebook` : "/courses"}
              className="text-xs font-semibold text-mm-blue-primary hover:underline"
            >
              Quay lại Bảng điểm học phần
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:h-[calc(100vh-108px)]">
            {/* Column 1: Student Artifact & Diff (4 cols) */}
            <div className="lg:col-span-4 lg:h-full overflow-hidden">
              <SubmissionArtifactViewer
                workspace={workspace}
                onSelectVersion={(subId) => requestSwitchSubmission(subId)}
                highlightedRef={highlightedRef}
              />
            </div>

            {/* Column 2: AI Digest & Viva Evidence (4 cols) */}
            <div className="lg:col-span-4 lg:h-full overflow-hidden">
              <VivaEvidenceColumn
                workspace={workspace}
                highlightedRef={highlightedRef}
              />
            </div>

            {/* Column 3: Interactive Rubric & Feedback (4 cols) */}
            <div className="lg:col-span-4 lg:h-full overflow-hidden">
              <RubricFeedbackCockpit
                workspace={workspace}
                aiProposal={aiProposal}
                loadingAi={loadingAi}
                officialScore={officialScore}
                rubricScores={rubricScores}
                feedbackText={feedbackText}
                overrideReason={overrideReason}
                voiceFeedbackUrl={voiceFeedbackUrl}
                draftSavedAt={draftSavedAt}
                savingGrade={savingGrade}
                onRequestAiProposal={() => void handleRequestAiProposal()}
                onChangeOfficialScore={(val) => {
                  setOfficialScore(val);
                  setIsDirty(true);
                }}
                onChangeRubricScores={(next, computedTotal) => {
                  setRubricScores(next);
                  setOfficialScore(String(computedTotal));
                  setIsDirty(true);
                }}
                onChangeFeedback={(val) => {
                  setFeedbackText(val);
                  setIsDirty(true);
                }}
                onChangeOverrideReason={(val) => {
                  setOverrideReason(val);
                  setIsDirty(true);
                }}
                onChangeVoiceFeedbackUrl={(url) => {
                  setVoiceFeedbackUrl(url);
                  setIsDirty(true);
                }}
                onHighlightCitation={(ref) => setHighlightedRef(ref)}
                onSaveAndNext={(moveNext) => void handleSaveAndNext(moveNext)}
              />
            </div>
          </div>
        )}
      </main>

      {/* E-SPEED-02 Unsaved Changes Confirmation Modal */}
      {pendingNavTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-mm-display text-base font-bold text-mm-dark">
                  Bạn có thay đổi chưa lưu (E-SPEED-02)
                </h3>
                <p className="mt-1 text-xs text-[#4b5563] leading-relaxed">
                  Điểm số hoặc nhận xét bạn vừa nhập cho sinh viên hiện tại chưa được lưu chính thức. Bạn có muốn hủy thay đổi để chuyển sang bài nộp khác không?
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => setPendingNavTarget(null)}
              >
                Ở lại chấm tiếp
              </MmButton>
              <MmButton variant="primary" size="sm" onClick={confirmDiscardAndSwitch}>
                Hủy thay đổi & Chuyển bài
              </MmButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
