/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  CloudOff,
  Flag,
  KeyRound,
  Maximize2,
  Send,
  ShieldAlert,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type {
  ActiveSessionResponse,
  AttemptStartResponse,
  LocalExamDraft,
  QuizDetailResponse,
  StudentAnswersMap,
  ViolationEventPayload,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MathCodeContent } from "../../components/MathCodeContent";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import {
  formatCountdown,
  formatDateTime,
  getDraftStorageKey,
  getLastSubmissionStorageKey,
  QUESTION_TYPE_LABELS,
  SECURITY_MODE_LABELS,
  toNumeric,
} from "./examHelpers";

type SyncStatus = "idle" | "saving" | "saved" | "offline" | "error";

function readLocalDraft(submissionId: string): LocalExamDraft | null {
  try {
    const raw = localStorage.getItem(getDraftStorageKey(submissionId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LocalExamDraft>;
    if (
      parsed &&
      parsed.submission_id === submissionId &&
      typeof parsed.seq_num === "number" &&
      parsed.answers &&
      typeof parsed.answers === "object"
    ) {
      return {
        submission_id: parsed.submission_id,
        quiz_id: String(parsed.quiz_id ?? ""),
        seq_num: parsed.seq_num,
        answers: parsed.answers as StudentAnswersMap,
        flagged_questions: Array.isArray(parsed.flagged_questions)
          ? parsed.flagged_questions.filter((v): v is string => typeof v === "string")
          : [],
        updated_at: String(parsed.updated_at ?? new Date().toISOString()),
      };
    }
    return null;
  } catch {
    return null;
  }
}

function writeLocalDraft(draft: LocalExamDraft): void {
  try {
    localStorage.setItem(getDraftStorageKey(draft.submission_id), JSON.stringify(draft));
  } catch {
    // Ignore storage quota errors gracefully
  }
}

function hasAnswerValue(value: string | string[] | undefined): boolean {
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  return false;
}

export const ExamTakingPage: React.FC = () => {
  const { courseId = "", quizId = "" } = useParams<{
    courseId: string;
    quizId: string;
  }>();
  const navigate = useNavigate();

  // Pre-exam gate state
  const [quizInfo, setQuizInfo] = useState<QuizDetailResponse | null>(null);
  const [activeSession, setActiveSession] = useState<ActiveSessionResponse | null>(
    null
  );
  const [loadingGate, setLoadingGate] = useState(true);
  const [passcodeInput, setPasscodeInput] = useState("");
  const [starting, setStarting] = useState(false);
  const [gateError, setGateError] = useState<string | null>(null);

  // Active exam state
  const [attempt, setAttempt] = useState<AttemptStartResponse | null>(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<StudentAnswersMap>({});
  const [flagged, setFlagged] = useState<string[]>([]);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [violationBanner, setViolationBanner] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(
    Boolean(document.fullscreenElement)
  );
  const [tabBlurCount, setTabBlurCount] = useState(0);
  const [fullscreenExitCount, setFullscreenExitCount] = useState(0);

  // Submit modal state
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Mutable refs for race-free 2-tier autosave
  const seqRef = useRef(0);
  const answersRef = useRef<StudentAnswersMap>({});
  const flaggedRef = useRef<string[]>([]);
  const pendingTabBlurDeltaRef = useRef(0);
  const pendingFullscreenDeltaRef = useRef(0);
  const pendingViolationRef = useRef<ViolationEventPayload | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const autoSubmittedRef = useRef(false);

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  useEffect(() => {
    flaggedRef.current = flagged;
  }, [flagged]);

  // Load quiz metadata & active session status for the gate
  useEffect(() => {
    if (!quizId) return;
    let mounted = true;
    setLoadingGate(true);
    Promise.all([
      examinationService.getQuizDetail(quizId),
      examinationService.getActiveSession(quizId).catch(() => null),
    ])
      .then(([detail, session]) => {
        if (!mounted) return;
        setQuizInfo(detail);
        setActiveSession(session);
      })
      .catch((err) => {
        if (!mounted) return;
        setGateError(
          err instanceof ApiError
            ? err.message
            : "Không thể tải thông tin phòng thi."
        );
      })
      .finally(() => {
        if (mounted) setLoadingGate(false);
      });

    return () => {
      mounted = false;
    };
  }, [quizId]);

  // Flush current state to POST /autosave
  const flushAutosave = useCallback(
    async (submissionId: string) => {
      if (!navigator.onLine) {
        setIsOffline(true);
        setSyncStatus("offline");
        return;
      }

      const currentSeq = Math.max(1, seqRef.current);
      seqRef.current = currentSeq;

      const tabDelta = pendingTabBlurDeltaRef.current;
      const fsDelta = pendingFullscreenDeltaRef.current;
      const violationEvent = pendingViolationRef.current;

      pendingTabBlurDeltaRef.current = 0;
      pendingFullscreenDeltaRef.current = 0;
      pendingViolationRef.current = null;

      setSyncStatus("saving");
      try {
        const res = await examinationService.autosaveAttempt(submissionId, {
          seq_num: currentSeq,
          answers: answersRef.current,
          flagged_questions: flaggedRef.current,
          tab_blur_delta: tabDelta,
          fullscreen_exit_delta: fsDelta,
          violation_event: violationEvent,
        });
        setRemainingSeconds(res.remaining_seconds);
        setTabBlurCount(res.tab_blur_count);
        setFullscreenExitCount(res.fullscreen_exit_count);
        setIsOffline(false);
        setSyncStatus("saved");
      } catch (err) {
        // Restore unsent violation deltas if network dropped
        pendingTabBlurDeltaRef.current += tabDelta;
        pendingFullscreenDeltaRef.current += fsDelta;
        if (violationEvent && !pendingViolationRef.current) {
          pendingViolationRef.current = violationEvent;
        }

        if (err instanceof ApiError && err.code === "NETWORK_ERROR") {
          setIsOffline(true);
          setSyncStatus("offline");
        } else {
          setSyncStatus("error");
        }
      }
    },
    []
  );

  // Schedule 2-tier autosave: immediate localStorage + 300ms debounced server POST
  const persistAndScheduleSync = useCallback(
    (nextAnswers: StudentAnswersMap, nextFlagged: string[]) => {
      if (!attempt) return;
      const nextSeq = seqRef.current + 1;
      seqRef.current = nextSeq;
      answersRef.current = nextAnswers;
      flaggedRef.current = nextFlagged;

      writeLocalDraft({
        submission_id: attempt.submission_id,
        quiz_id: attempt.quiz_id,
        seq_num: nextSeq,
        answers: nextAnswers,
        flagged_questions: nextFlagged,
        updated_at: new Date().toISOString(),
      });

      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
      }

      if (!navigator.onLine) {
        setIsOffline(true);
        setSyncStatus("offline");
        return;
      }

      setSyncStatus("saving");
      debounceTimerRef.current = window.setTimeout(() => {
        void flushAutosave(attempt.submission_id);
      }, 300);
    },
    [attempt, flushAutosave]
  );

  const requestFullscreenSafely = useCallback(async () => {
    try {
      if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } catch {
      // Some browsers restrict fullscreen in headless or embedded contexts
    }
  }, []);

  const handleStartExam = async (event: React.FormEvent) => {
    event.preventDefault();
    setGateError(null);
    setStarting(true);

    await requestFullscreenSafely();

    try {
      const started = await examinationService.startOrResumeAttempt(quizId, {
        passcode: passcodeInput.trim() || null,
      });

      localStorage.setItem(
        getLastSubmissionStorageKey(started.quiz_id),
        started.submission_id
      );

      // Resume Exam: compare localStorage seq_num vs server seq_num
      const localDraft = readLocalDraft(started.submission_id);
      let initialAnswers: StudentAnswersMap = started.student_answers ?? {};
      let initialFlagged: string[] = started.flagged_questions ?? [];
      let initialSeq = started.seq_num ?? 0;
      let shouldPushLocalToServer = false;

      if (localDraft && localDraft.seq_num > initialSeq) {
        initialAnswers = localDraft.answers;
        initialFlagged = localDraft.flagged_questions;
        initialSeq = localDraft.seq_num;
        shouldPushLocalToServer = true;
      } else {
        writeLocalDraft({
          submission_id: started.submission_id,
          quiz_id: started.quiz_id,
          seq_num: initialSeq,
          answers: initialAnswers,
          flagged_questions: initialFlagged,
          updated_at: new Date().toISOString(),
        });
      }

      seqRef.current = initialSeq;
      answersRef.current = initialAnswers;
      flaggedRef.current = initialFlagged;

      setAttempt(started);
      setAnswers(initialAnswers);
      setFlagged(initialFlagged);
      setRemainingSeconds(started.remaining_seconds);
      setCurrentIdx(0);
      setSyncStatus("saved");
      autoSubmittedRef.current = false;

      if (shouldPushLocalToServer) {
        showToast(
          "info",
          "Đã khôi phục bản nháp mới hơn từ thiết bị và đồng bộ lên máy chủ."
        );
        void flushAutosave(started.submission_id);
      } else if (started.resumed) {
        showToast("info", "Đã khôi phục phiên thi đang làm dở của bạn.");
      }
    } catch (err) {
      setGateError(
        err instanceof ApiError
          ? err.message
          : "Không thể bắt đầu phiên thi. Vui lòng thử lại."
      );
    } finally {
      setStarting(false);
    }
  };

  // Final submit handler
  const handleFinalSubmit = useCallback(
    async (isAutoTimeout = false) => {
      if (!attempt || submitting) return;
      setSubmitting(true);
      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
      }
      try {
        const res = await examinationService.submitAttempt(attempt.submission_id, {
          answers: answersRef.current,
          flagged_questions: flaggedRef.current,
        });
        localStorage.removeItem(getDraftStorageKey(attempt.submission_id));
        localStorage.setItem(
          getLastSubmissionStorageKey(attempt.quiz_id),
          res.submission_id
        );

        if (document.fullscreenElement && document.exitFullscreen) {
          document.exitFullscreen().catch(() => undefined);
        }

        showToast(
          "success",
          isAutoTimeout
            ? "Hết thời gian làm bài! Hệ thống đã tự động nộp bài của bạn."
            : "Đã nộp bài thi thành công!"
        );
        navigate(
          `/courses/${courseId}/exams/${quizId}/result?submissionId=${res.submission_id}`,
          { replace: true }
        );
      } catch (err) {
        showToast(
          "error",
          err instanceof ApiError
            ? err.message
            : "Không thể nộp bài thi. Dữ liệu vẫn được lưu trên thiết bị."
        );
        setSubmitting(false);
      }
    },
    [attempt, submitting, navigate, courseId, quizId]
  );

  // Server-synced countdown timer
  useEffect(() => {
    if (!attempt) return;
    const interval = window.setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          if (!autoSubmittedRef.current) {
            autoSubmittedRef.current = true;
            void handleFinalSubmit(true);
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [attempt, handleFinalSubmit]);

  // Online / Offline listeners for E-10 banner & automatic re-sync
  useEffect(() => {
    if (!attempt) return;
    const handleOffline = () => {
      setIsOffline(true);
      setSyncStatus("offline");
    };
    const handleOnline = () => {
      setIsOffline(false);
      showToast("info", "Đã khôi phục kết nối mạng. Đang đồng bộ bản nháp lên máy chủ...");
      void flushAutosave(attempt.submission_id);
    };

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [attempt, flushAutosave]);

  // Proctoring listeners: visibilitychange, blur, fullscreenchange, and copy/paste/contextmenu lock
  useEffect(() => {
    if (!attempt) return;
    const submissionId = attempt.submission_id;
    const isControlled = attempt.security_mode === "CONTROLLED";

    const reportViolation = (
      type: ViolationEventPayload["type"],
      message: string,
      opts: { tabBlur?: boolean; fsExit?: boolean }
    ) => {
      setViolationBanner(message);
      if (opts.tabBlur) pendingTabBlurDeltaRef.current += 1;
      if (opts.fsExit) pendingFullscreenDeltaRef.current += 1;
      pendingViolationRef.current = {
        type,
        timestamp: new Date().toISOString(),
        detail: message,
      };
      seqRef.current += 1;
      void flushAutosave(submissionId);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        reportViolation(
          "TAB_BLUR",
          "Cảnh báo chuyển tab / ẩn cửa sổ thi! Hệ thống đã ghi nhận vào nhật ký giám sát.",
          { tabBlur: true }
        );
      }
    };

    const handleWindowBlur = () => {
      if (!document.hidden) {
        reportViolation(
          "TAB_BLUR",
          "Cảnh báo rời tiêu điểm cửa sổ phòng thi! Hành vi này đã được ghi nhận.",
          { tabBlur: true }
        );
      }
    };

    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement);
      setIsFullscreen(active);
      if (!active) {
        reportViolation(
          "FULLSCREEN_EXIT",
          "Bạn vừa thoát chế độ toàn màn hình (Fullscreen). Vui lòng bật lại toàn màn hình để tiếp tục.",
          { fsExit: true }
        );
      }
    };

    const handleBlockClipboard = (event: ClipboardEvent) => {
      if (!isControlled) return;
      event.preventDefault();
      showToast(
        "error",
        "Chế độ phòng thi giám sát chặt (CONTROLLED) không cho phép sao chép hoặc dán nội dung."
      );
      reportViolation(
        "COPY_PASTE_ATTEMPT",
        "Hành vi sao chép/dán bị chặn trong chế độ CONTROLLED.",
        {}
      );
    };

    const handleBlockContextMenu = (event: MouseEvent) => {
      if (!isControlled) return;
      event.preventDefault();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleWindowBlur);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("copy", handleBlockClipboard);
    document.addEventListener("paste", handleBlockClipboard);
    document.addEventListener("cut", handleBlockClipboard);
    document.addEventListener("contextmenu", handleBlockContextMenu);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleWindowBlur);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("copy", handleBlockClipboard);
      document.removeEventListener("paste", handleBlockClipboard);
      document.removeEventListener("cut", handleBlockClipboard);
      document.removeEventListener("contextmenu", handleBlockContextMenu);
    };
  }, [attempt, flushAutosave]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const currentQuestion = attempt?.questions[currentIdx] ?? null;

  const answeredCount = useMemo(() => {
    if (!attempt) return 0;
    return attempt.questions.filter((q) => hasAnswerValue(answers[q.id])).length;
  }, [attempt, answers]);

  const handleSelectSingle = (questionId: string, optionKey: string) => {
    const nextAnswers: StudentAnswersMap = { ...answers, [questionId]: optionKey };
    setAnswers(nextAnswers);
    persistAndScheduleSync(nextAnswers, flagged);
  };

  const handleToggleMulti = (questionId: string, optionKey: string) => {
    const existing = answers[questionId];
    const currentList = Array.isArray(existing)
      ? existing
      : typeof existing === "string" && existing
        ? [existing]
        : [];
    const nextList = currentList.includes(optionKey)
      ? currentList.filter((k) => k !== optionKey)
      : [...currentList, optionKey];
    const nextAnswers: StudentAnswersMap = { ...answers, [questionId]: nextList };
    setAnswers(nextAnswers);
    persistAndScheduleSync(nextAnswers, flagged);
  };

  const handleToggleFlag = (questionId: string) => {
    const nextFlagged = flagged.includes(questionId)
      ? flagged.filter((id) => id !== questionId)
      : [...flagged, questionId];
    setFlagged(nextFlagged);
    persistAndScheduleSync(answers, nextFlagged);
  };

  // Pre-exam Gate Screen
  if (!attempt) {
    return (
      <div className="min-h-screen bg-mm-bg px-4 py-10">
        <div className="mx-auto max-w-xl space-y-6">
          <Link
            to={`/courses/${courseId}/exams`}
            className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Quay lại danh sách kỳ thi</span>
          </Link>

          <MmCard variant="ambient" radius="card-lg" padding="lg">
            {loadingGate ? (
              <div className="space-y-3 py-8">
                <div className="h-7 w-2/3 animate-pulse rounded-mm-btn bg-mm-divider" />
                <div className="h-24 animate-pulse rounded-mm-panel bg-mm-divider/60" />
              </div>
            ) : !quizInfo ? (
              <div className="py-8 text-center">
                <AlertCircle className="mx-auto mb-3 h-10 w-10 text-mm-danger" />
                <p className="font-mm-ui text-sm text-mm-text-secondary">
                  {gateError || "Không tìm thấy thông tin kỳ thi."}
                </p>
              </div>
            ) : (
              <form onSubmit={handleStartExam} className="space-y-5">
                <div>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1 rounded-full bg-mm-blue-light/30 px-3 py-0.5 font-mm-ui text-xs font-medium text-mm-blue-hover">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      {SECURITY_MODE_LABELS[quizInfo.security_mode]}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-mm-divider px-3 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                      <Clock className="h-3.5 w-3.5" />
                      {quizInfo.time_limit_mins} phút · {quizInfo.question_count} câu
                    </span>
                  </div>
                  <h1 className="font-mm-display text-[26px] font-semibold tracking-tight text-mm-heading">
                    {quizInfo.title}
                  </h1>
                  <p className="mt-1 font-mm-ui text-xs text-mm-text-secondary">
                    Thời gian mở đề: {formatDateTime(quizInfo.available_from)} —{" "}
                    {formatDateTime(quizInfo.available_until)}
                  </p>
                </div>

                {activeSession?.has_active_session && (
                  <div className="flex items-start gap-2.5 rounded-mm-panel border border-mm-blue-hover/30 bg-mm-blue-light/20 px-4 py-3 text-mm-blue-deep">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="font-mm-ui text-sm">
                      Bạn đang có một phiên thi chưa nộp. Bấm tiếp tục để khôi phục bài làm và bản nháp đã lưu.
                    </div>
                  </div>
                )}

                {gateError && (
                  <div
                    role="alert"
                    className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
                  >
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span className="font-mm-ui text-sm">{gateError}</span>
                  </div>
                )}

                <div className="rounded-mm-panel border border-mm-border bg-mm-divider/30 p-4 font-mm-ui text-xs leading-relaxed text-mm-text-secondary">
                  <p className="mb-1.5 font-medium text-mm-heading">
                    Quy chế phòng thi trực tuyến ADLAS:
                  </p>
                  <ul className="list-disc space-y-1 pl-4">
                    <li>
                      Trình duyệt sẽ tự động kích hoạt chế độ toàn màn hình (Fullscreen) khi bắt đầu.
                    </li>
                    <li>
                      Mọi thao tác chuyển tab, rời cửa sổ hoặc thoát Fullscreen đều được ghi nhận về máy chủ.
                    </li>
                    <li>
                      Đáp án được tự động lưu tức thì trên thiết bị và đồng bộ liên tục lên máy chủ (Autosave 2 tầng).
                    </li>
                    {quizInfo.is_ai_locked && (
                      <li>
                        Gia sư AI và tài liệu môn học được tạm khóa trong suốt thời gian làm bài (E-13).
                      </li>
                    )}
                  </ul>
                </div>

                {quizInfo.has_passcode && !activeSession?.has_active_session && (
                  <FormField
                    label="Mật khẩu phòng thi (Passcode)"
                    htmlFor="exam-passcode"
                    required
                    helper="Nhập đúng mật khẩu do Giảng viên cung cấp tại phòng thi"
                  >
                    <div className="relative">
                      <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mm-text-muted" />
                      <input
                        id="exam-passcode"
                        type="text"
                        autoFocus
                        value={passcodeInput}
                        onChange={(e) => setPasscodeInput(e.target.value)}
                        placeholder="Nhập mật khẩu phòng thi..."
                        className={`${mmInputClass(false)} pl-9 font-mm-mono`}
                      />
                    </div>
                  </FormField>
                )}

                <MmButton
                  type="submit"
                  variant="brand"
                  size="lg"
                  fullWidth
                  loading={starting}
                >
                  <Maximize2 className="h-4 w-4" />
                  <span>
                    {activeSession?.has_active_session
                      ? "Tiếp tục bài thi & Bật toàn màn hình"
                      : "Bắt đầu làm bài & Bật toàn màn hình"}
                  </span>
                </MmButton>
              </form>
            )}
          </MmCard>
        </div>
      </div>
    );
  }

  const isCriticalTime = remainingSeconds < 300;
  const unansweredCount = attempt.questions.length - answeredCount;

  return (
    <div className="min-h-screen bg-mm-bg">
      {/* Sticky Exam Header */}
      <header className="sticky top-0 z-30 border-b border-mm-border bg-mm-bg/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <h1 className="truncate font-mm-mid text-base font-medium text-mm-heading sm:text-lg">
              {quizInfo?.title ?? "Phòng thi trực tuyến"}
            </h1>
            <p className="font-mm-ui text-xs text-mm-text-muted">
              Lượt thi #{attempt.attempt_number} · Đã làm {answeredCount}/
              {attempt.questions.length} câu
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Autosave Badge */}
            <div
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mm-ui text-xs font-medium ${
                syncStatus === "offline"
                  ? "bg-mm-warning-bg text-mm-warning"
                  : syncStatus === "error"
                    ? "bg-mm-danger-bg text-mm-danger"
                    : syncStatus === "saving"
                      ? "bg-mm-blue-light/30 text-mm-blue-hover"
                      : "bg-mm-success-bg text-mm-success"
              }`}
            >
              {syncStatus === "offline" ? (
                <>
                  <CloudOff className="h-3.5 w-3.5" />
                  <span>Lưu cục bộ (Offline)</span>
                </>
              ) : syncStatus === "saving" ? (
                <span>Đang đồng bộ...</span>
              ) : syncStatus === "error" ? (
                <span>Chờ đồng bộ lại</span>
              ) : (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Đã lưu tự động</span>
                </>
              )}
            </div>

            {/* Countdown Clock */}
            <div
              className={`inline-flex items-center gap-1.5 rounded-mm-btn border px-3.5 py-1.5 font-mm-mono text-base font-medium ${
                isCriticalTime
                  ? "animate-pulse border-mm-danger bg-mm-danger-bg text-mm-danger"
                  : "border-mm-border bg-mm-divider/40 text-mm-heading"
              }`}
            >
              <Clock className="h-4 w-4" />
              <span>{formatCountdown(remainingSeconds)}</span>
            </div>

            {!isFullscreen && (
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => void requestFullscreenSafely()}
              >
                <Maximize2 className="h-4 w-4" />
                <span className="hidden sm:inline">Toàn màn hình</span>
              </MmButton>
            )}

            <MmButton
              variant="brand"
              size="sm"
              onClick={() => setSubmitModalOpen(true)}
            >
              <Send className="h-4 w-4" />
              <span>Nộp bài</span>
            </MmButton>
          </div>
        </div>
      </header>

      {/* Banners: Offline E-10 & Proctoring Violations */}
      <div className="mx-auto max-w-7xl space-y-2 px-4 pt-4 sm:px-6">
        {isOffline && (
          <div
            role="alert"
            className="flex items-center gap-2.5 rounded-mm-panel border border-mm-warning/40 bg-mm-warning-bg px-4 py-3 text-mm-warning"
          >
            <WifiOff className="h-4 w-4 shrink-0" />
            <span className="font-mm-ui text-sm font-medium">
              [E-10] Mất kết nối mạng! Đáp án của bạn vẫn đang được lưu an toàn trên thiết bị và sẽ tự động đồng bộ ngay khi có mạng trở lại.
            </span>
          </div>
        )}

        {violationBanner && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
          >
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              <span className="font-mm-ui text-sm">
                {violationBanner} (Chuyển tab: {tabBlurCount} · Thoát Fullscreen:{" "}
                {fullscreenExitCount})
              </span>
            </div>
            <div className="flex items-center gap-2">
              {!isFullscreen && (
                <MmButton
                  variant="danger"
                  size="sm"
                  onClick={() => void requestFullscreenSafely()}
                >
                  Bật lại toàn màn hình
                </MmButton>
              )}
              <button
                type="button"
                onClick={() => setViolationBanner(null)}
                className="font-mm-ui text-xs underline"
              >
                Đã hiểu
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main 2-Column Exam Workspace */}
      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-12">
        {/* Left: Question Area */}
        <section className="space-y-4 lg:col-span-8">
          {currentQuestion && (
            <MmCard variant="standard" radius="card" padding="lg">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-mm-divider pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-mm-dark px-3 py-1 font-mm-mono text-xs font-medium text-white">
                    Câu {currentIdx + 1} / {attempt.questions.length}
                  </span>
                  <span className="rounded-mm-tag bg-mm-divider px-2.5 py-1 font-mm-ui text-xs text-mm-text-secondary">
                    {QUESTION_TYPE_LABELS[currentQuestion.question_type]}
                  </span>
                  <span className="font-mm-data text-xs text-mm-text-muted">
                    {toNumeric(currentQuestion.default_points)} điểm
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => handleToggleFlag(currentQuestion.id)}
                  className={`inline-flex items-center gap-1.5 rounded-mm-btn border px-3 py-1.5 font-mm-ui text-xs font-medium transition-colors ${
                    flagged.includes(currentQuestion.id)
                      ? "border-mm-warning bg-mm-warning-bg text-mm-warning"
                      : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/40"
                  }`}
                >
                  <Flag className="h-3.5 w-3.5" />
                  <span>
                    {flagged.includes(currentQuestion.id)
                      ? "Đã cắm cờ xem lại"
                      : "Cắm cờ xem lại"}
                  </span>
                </button>
              </div>

              <div className="mb-6">
                <MathCodeContent
                  content={currentQuestion.question_text}
                  className="text-base text-mm-heading"
                />
              </div>

              <div className="space-y-3">
                {currentQuestion.options_snapshot.map((opt) => {
                  const key = opt.key;
                  const ans = answers[currentQuestion.id];
                  const isSelected =
                    currentQuestion.question_type === "MULTI_SELECT"
                      ? Array.isArray(ans) && ans.includes(key)
                      : ans === key;

                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() =>
                        currentQuestion.question_type === "MULTI_SELECT"
                          ? handleToggleMulti(currentQuestion.id, key)
                          : handleSelectSingle(currentQuestion.id, key)
                      }
                      className={`flex w-full items-start gap-3 rounded-mm-panel border p-4 text-left transition-all ${
                        isSelected
                          ? "border-mm-blue-hover bg-mm-blue-light/20 ring-1 ring-mm-blue-hover/30"
                          : "border-mm-border bg-mm-bg hover:border-mm-blue-400 hover:bg-mm-divider/20"
                      }`}
                    >
                      <span
                        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mm-mono text-xs font-medium ${
                          isSelected
                            ? "bg-mm-blue-hover text-white"
                            : "bg-mm-divider text-mm-heading"
                        }`}
                      >
                        {key}
                      </span>
                      <MathCodeContent
                        content={opt.text}
                        inline
                        className="pt-0.5 text-sm text-mm-heading"
                      />
                    </button>
                  );
                })}
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-mm-divider pt-4">
                <MmButton
                  variant="secondary"
                  disabled={currentIdx === 0}
                  onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Câu trước</span>
                </MmButton>

                {currentIdx < attempt.questions.length - 1 ? (
                  <MmButton
                    variant="brand"
                    onClick={() =>
                      setCurrentIdx((i) =>
                        Math.min(attempt.questions.length - 1, i + 1)
                      )
                    }
                  >
                    <span>Câu tiếp theo</span>
                    <ChevronRight className="h-4 w-4" />
                  </MmButton>
                ) : (
                  <MmButton
                    variant="brand"
                    onClick={() => setSubmitModalOpen(true)}
                  >
                    <Send className="h-4 w-4" />
                    <span>Hoàn thành & Nộp bài</span>
                  </MmButton>
                )}
              </div>
            </MmCard>
          )}
        </section>

        {/* Right: Question Palette Grid */}
        <aside className="lg:col-span-4">
          <MmCard variant="standard" radius="card" padding="md" className="sticky top-24">
            <h2 className="font-mm-mid text-base font-medium text-mm-heading">
              Bảng điều hướng câu hỏi
            </h2>
            <p className="mt-0.5 font-mm-ui text-xs text-mm-text-secondary">
              Bấm vào số thứ tự để chuyển nhanh tới câu hỏi
            </p>

            <div className="mt-4 grid grid-cols-5 gap-2">
              {attempt.questions.map((q, idx) => {
                const isCurrent = idx === currentIdx;
                const isFlagged = flagged.includes(q.id);
                const isAnswered = hasAnswerValue(answers[q.id]);

                let styleClass =
                  "border-mm-border bg-mm-bg text-mm-heading hover:bg-mm-divider/40";
                if (isFlagged) {
                  styleClass =
                    "border-mm-warning bg-mm-warning-bg text-mm-warning";
                } else if (isAnswered) {
                  styleClass =
                    "border-mm-blue-hover bg-mm-blue-hover text-white";
                }

                return (
                  <button
                    key={q.id}
                    type="button"
                    onClick={() => setCurrentIdx(idx)}
                    className={`relative flex h-10 items-center justify-center rounded-mm-btn border font-mm-mono text-sm font-medium transition-all ${styleClass} ${
                      isCurrent ? "ring-2 ring-mm-dark ring-offset-1" : ""
                    }`}
                  >
                    {idx + 1}
                    {isFlagged && (
                      <span
                        aria-hidden="true"
                        className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-mm-warning"
                      />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="mt-5 space-y-2 border-t border-mm-divider pt-4 font-mm-ui text-xs text-mm-text-secondary">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <span className="h-3 w-3 rounded bg-mm-blue-hover" />
                  Đã trả lời
                </span>
                <span className="font-mm-data font-medium text-mm-heading">
                  {answeredCount}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <span className="h-3 w-3 rounded border border-mm-border bg-mm-bg" />
                  Chưa trả lời
                </span>
                <span className="font-mm-data font-medium text-mm-heading">
                  {unansweredCount}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <span className="h-3 w-3 rounded border border-mm-warning bg-mm-warning-bg" />
                  Đã cắm cờ xem lại
                </span>
                <span className="font-mm-data font-medium text-mm-heading">
                  {flagged.length}
                </span>
              </div>
            </div>

            <div className="mt-5">
              <MmButton
                variant="primary"
                fullWidth
                onClick={() => setSubmitModalOpen(true)}
              >
                <Send className="h-4 w-4" />
                <span>Nộp bài thi</span>
              </MmButton>
            </div>
          </MmCard>
        </aside>
      </main>

      {/* Confirm Submit Modal */}
      <MmModal
        open={submitModalOpen}
        title="Xác nhận nộp bài thi?"
        subtitle="Sau khi nộp bài, hệ thống sẽ khóa bài làm và tiến hành chấm điểm tự động."
        onClose={() => !submitting && setSubmitModalOpen(false)}
        footer={
          <>
            <MmButton
              variant="secondary"
              disabled={submitting}
              onClick={() => setSubmitModalOpen(false)}
            >
              Tiếp tục làm bài
            </MmButton>
            <MmButton
              variant="brand"
              loading={submitting}
              onClick={() => void handleFinalSubmit(false)}
            >
              Xác nhận nộp bài
            </MmButton>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3">
              <p className="font-mm-data text-2xl font-medium text-mm-blue-hover">
                {answeredCount}
              </p>
              <p className="font-mm-ui text-xs text-mm-text-secondary">
                Đã trả lời
              </p>
            </div>
            <div className="rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3">
              <p className="font-mm-data text-2xl font-medium text-mm-danger">
                {unansweredCount}
              </p>
              <p className="font-mm-ui text-xs text-mm-text-secondary">
                Chưa làm
              </p>
            </div>
            <div className="rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3">
              <p className="font-mm-data text-2xl font-medium text-mm-warning">
                {flagged.length}
              </p>
              <p className="font-mm-ui text-xs text-mm-text-secondary">
                Đang cắm cờ
              </p>
            </div>
          </div>

          {unansweredCount > 0 && (
            <div className="flex items-start gap-2 rounded-mm-panel border border-mm-warning/40 bg-mm-warning-bg px-3.5 py-2.5 text-mm-warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="font-mm-ui text-sm">
                Bạn vẫn còn {unansweredCount} câu chưa chọn đáp án. Bạn có chắc chắn muốn nộp bài ngay không?
              </span>
            </div>
          )}
        </div>
      </MmModal>
    </div>
  );
};
