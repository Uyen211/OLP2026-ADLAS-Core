/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  Clock,
  Eye,
  Lock,
  MessageSquare,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";

import { assessmentService } from "../../../../services/assessmentService";
import type { VivaQuestion, VivaStartResponse, VivaViolationLog } from "../../../../types/assessment";
import { useAuthStore } from "../../../../stores/authStore";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

export const VivaSandboxPage: React.FC = () => {
  const { submissionId } = useParams<{ submissionId: string }>();
  const navigate = useNavigate();
  const me = useAuthStore((s) => s.me);

  // Session State
  const [sessionData, setSessionData] = useState<VivaStartResponse | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<VivaQuestion | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Candidate Answer State
  const [answerText, setAnswerText] = useState<string>("");
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());

  // Security Monitoring State
  const [showBriefingModal, setShowBriefingModal] = useState<boolean>(true);
  const [briefingAccepted, setBriefingAccepted] = useState<boolean>(false);
  const [shakeInput, setShakeInput] = useState<boolean>(false);
  const [windowBlurWarning, setWindowBlurWarning] = useState<boolean>(false);
  const [lastBlurTimestamp, setLastBlurTimestamp] = useState<string>("");
  const [preparingSession, setPreparingSession] = useState<boolean>(false);
  const [showViolationsModal, setShowViolationsModal] = useState<boolean>(false);
  const [violationLogs, setViolationLogs] = useState<VivaViolationLog[]>([]);

  // Timer State
  const [remainingSeconds, setRemainingSeconds] = useState<number>(900);
  const timerRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const handleTimeExpireRef = useRef<() => void>(() => {});

  // Word count calculation
  const wordCount = useMemo(() => {
    const trimmed = answerText.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }, [answerText]);

  // Start or resume Viva session
  const initSession = useCallback(async () => {
    if (!submissionId) return;
    try {
      setLoading(true);
      setPreparingSession(false);
      const data = await assessmentService.startVivaSession(submissionId);
      setSessionData(data);
      setCurrentQuestion(data.question);
      setRemainingSeconds(
        typeof data.remaining_seconds === "number"
          ? data.remaining_seconds
          : data.total_duration_seconds || 900
      );
      setQuestionStartTime(Date.now());
      if (data.violation_logs) {
        setViolationLogs(data.violation_logs);
      }
      if (data.status === "COMPLETED" || data.status === "TIMEOUT") {
        setIsCompleted(true);
        setShowBriefingModal(false);
      }
    } catch (err: any) {
      if (err?.code === "E-VIVA-03" || err?.code === "E-VIVA-04") {
        setIsCompleted(true);
        setShowBriefingModal(false);
        return;
      }
      if (err?.code === "E-VIVA-PREPARING") {
        setPreparingSession(true);
        return;
      }
      toast.error(resolveErrorMessage(err?.code, "Không thể khởi tạo phiên vấn đáp Viva."));
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    void initSession();
  }, [initSession]);

  useEffect(() => {
    if (!preparingSession) return;
    const retryTimer = window.setTimeout(() => {
      void initSession();
    }, 2500);
    return () => window.clearTimeout(retryTimer);
  }, [preparingSession, initSession]);

  // Handle Timeout
  const handleTimeExpire = useCallback(async () => {
    if (!submissionId) return;
    toast.error("Hết giờ làm bài vấn đáp! Hệ thống đang tự động niêm phong phiên thi...");
    try {
      const timeSpent = Math.max(0, Math.floor((Date.now() - questionStartTime) / 1000));
      await assessmentService.timeoutVivaSession(submissionId, {
        question_id: currentQuestion?.id,
        answer_text: answerText.trim() || undefined,
        time_spent_seconds: timeSpent,
      });
    } catch {
      // Even if network fails, seal UI state
    } finally {
      setIsCompleted(true);
    }
  }, [submissionId, currentQuestion, answerText, questionStartTime]);

  useEffect(() => {
    handleTimeExpireRef.current = () => {
      void handleTimeExpire();
    };
  }, [handleTimeExpire]);

  // Overall Countdown Timer (created once when briefing is accepted)
  useEffect(() => {
    if (!briefingAccepted || isCompleted) return;

    timerRef.current = window.setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          handleTimeExpireRef.current();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [briefingAccepted, isCompleted]);

  // Window Blur Violation Trap (E-VIVA-01)
  useEffect(() => {
    if (!briefingAccepted || isCompleted) return;

    const handleBlur = () => {
      const nowIso = new Date().toISOString();
      const newLog: VivaViolationLog = {
        type: "WINDOW_BLUR",
        timestamp: nowIso,
        details: { reason: "Mất tiêu điểm cửa sổ / Chuyển tab hoặc ứng dụng" },
      };
      setViolationLogs((prev) => [newLog, ...prev]);
      setLastBlurTimestamp(new Date().toLocaleTimeString("vi-VN"));
      setWindowBlurWarning(true);

      if (submissionId) {
        assessmentService
          .recordSecurityViolation(submissionId, {
            violation_type: "WINDOW_BLUR",
            details: { timestamp: nowIso },
          })
          .catch(() => {});
      }
    };

    window.addEventListener("blur", handleBlur);
    return () => {
      window.removeEventListener("blur", handleBlur);
    };
  }, [briefingAccepted, isCompleted, submissionId]);

  // Clipboard Paste Lock (BR-VIVA-01 / E-9)
  const triggerPasteBlock = useCallback((e: React.SyntheticEvent) => {
    e.preventDefault();
    setShakeInput(true);

    const nowIso = new Date().toISOString();
    const newLog: VivaViolationLog = {
      type: "PASTE_ATTEMPT",
      timestamp: nowIso,
      details: { reason: "Cố gắng dán nội dung từ Clipboard (Ctrl+V / Paste)" },
    };
    setViolationLogs((prev) => [newLog, ...prev]);
    toast.error(resolveErrorMessage("E-9"));

    if (submissionId) {
      assessmentService
        .recordSecurityViolation(submissionId, {
          violation_type: "PASTE_ATTEMPT",
          details: { timestamp: nowIso },
        })
        .catch(() => {});
    }

    setTimeout(() => {
      setShakeInput(false);
    }, 600);
  }, [submissionId]);

  // Handle Keydown for Paste shortcuts (Ctrl+V, Cmd+V, Shift+Insert)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") {
      triggerPasteBlock(e);
    } else if (e.shiftKey && e.key === "Insert") {
      triggerPasteBlock(e);
    }
  };

  // Submit Answer
  const handleSubmitAnswer = async () => {
    if (!currentQuestion || !submissionId) return;

    if (wordCount < 50) {
      toast.error(resolveErrorMessage("E-VIVA-WORD-COUNT"));
      textareaRef.current?.focus();
      return;
    }

    try {
      setSubmitting(true);
      const timeSpent = Math.max(0, Math.floor((Date.now() - questionStartTime) / 1000));

      const res = await assessmentService.submitVivaAnswer(submissionId, {
        question_id: currentQuestion.id,
        answer_text: answerText.trim(),
        time_spent_seconds: timeSpent,
      });

      toast.success("Đã ghi nhận câu trả lời!");

      if (res.is_completed || !res.next_question) {
        setIsCompleted(true);
      } else {
        setCurrentQuestion(res.next_question);
        setAnswerText("");
        setQuestionStartTime(Date.now());
        textareaRef.current?.focus();
      }
    } catch (err: any) {
      toast.error(resolveErrorMessage(err?.code, err?.message || "Lỗi khi gửi câu trả lời."));
    } finally {
      setSubmitting(false);
    }
  };

  const formattedTime = useMemo(() => {
    const mins = Math.floor(remainingSeconds / 60);
    const secs = remainingSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }, [remainingSeconds]);

  if (loading || preparingSession) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-mm-blue-primary border-t-transparent" />
          <span className="font-mm-ui text-sm text-[#6b7280]">
            {preparingSession
              ? "AI đang hoàn tất phân tích bài nộp để sinh câu hỏi vấn đáp..."
              : "Đang khởi tạo phòng thi Viva Sandbox an toàn..."}
          </span>
        </div>
      </div>
    );
  }

  // Pre-exam Security Briefing Modal
  if (showBriefingModal && !isCompleted) {
    return (
      <MmModal
        open={showBriefingModal}
        onClose={() => navigate(-1)}
        title="Quy chế phòng thi Vấn đáp Viva Sandbox"
        maxWidthClass="max-w-2xl"
      >
        <div className="space-y-4 text-xs font-mm-ui text-mm-dark">
          <div className="rounded-xl border border-[#dbeafe] bg-[#f8fbff] p-4 text-[#1e40af] flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-mm-blue-primary flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-sm text-mm-dark">Khảo thí Độc bản & Giám sát Tự động (OLP 2026)</p>
              <p className="mt-1 leading-relaxed text-xs text-[#4b5563]">
                Hệ thống AI đóng vai trò Hội đồng phản biện, đặt câu hỏi trực tiếp dựa trên chính đề tài, mã nguồn và tài liệu bài làm cụ thể mà bạn đã nộp.
              </p>
            </div>
          </div>

          <div className="space-y-2.5">
            <h4 className="font-semibold text-mm-dark uppercase tracking-wider text-[11px]">
              Quy tắc bắt buộc trong phòng thi:
            </h4>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <div className="rounded-xl border border-[#e5e7eb] p-3 bg-white">
                <div className="flex items-center gap-2 font-semibold text-mm-dark">
                  <Lock className="h-4 w-4 text-mm-blue-primary" />
                  <span>Khóa Clipboard (BR-VIVA-01)</span>
                </div>
                <p className="mt-1 text-[#6b7280] text-[11px] leading-relaxed">
                  Mọi thao tác dán nội dung (Ctrl+V) bị vô hiệu hóa. Câu trả lời phải do thí sinh tự gõ trực tiếp.
                </p>
              </div>

              <div className="rounded-xl border border-[#e5e7eb] p-3 bg-white">
                <div className="flex items-center gap-2 font-semibold text-mm-dark">
                  <Eye className="h-4 w-4 text-mm-blue-primary" />
                  <span>Giám sát chuyển cửa sổ</span>
                </div>
                <p className="mt-1 text-[#6b7280] text-[11px] leading-relaxed">
                  Mọi hành vi chuyển tab hoặc rời phòng thi đều được ghi nhận chi tiết thời điểm vào nhật ký giám sát.
                </p>
              </div>

              <div className="rounded-xl border border-[#e5e7eb] p-3 bg-white">
                <div className="flex items-center gap-2 font-semibold text-mm-dark">
                  <MessageSquare className="h-4 w-4 text-mm-blue-primary" />
                  <span>Độ dài tối thiểu (&ge; 50 từ)</span>
                </div>
                <p className="mt-1 text-[#6b7280] text-[11px] leading-relaxed">
                  Mỗi câu trả lời cần đạt tối thiểu 50 từ để chứng minh chiều sâu tư duy và năng lực thực chất.
                </p>
              </div>

              <div className="rounded-xl border border-[#e5e7eb] p-3 bg-white">
                <div className="flex items-center gap-2 font-semibold text-mm-dark">
                  <Clock className="h-4 w-4 text-mm-blue-primary" />
                  <span>Quy trình 1 chiều cố định</span>
                </div>
                <p className="mt-1 text-[#6b7280] text-[11px] leading-relaxed">
                  Sau khi nộp câu trả lời, hệ thống chuyển sang câu tiếp theo và không thể quay lại sửa câu trước.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#f3f4f6]">
            <MmButton variant="ghost" onClick={() => navigate(-1)}>
              Quay lại
            </MmButton>
            <MmButton
              variant="brand"
              onClick={() => {
                setShowBriefingModal(false);
                setBriefingAccepted(true);
                setQuestionStartTime(Date.now());
              }}
              className="rounded-full shadow-sm"
            >
              <ShieldCheck className="h-4 w-4 mr-1.5" />
              Tôi đã hiểu & Bắt đầu làm bài
            </MmButton>
          </div>
        </div>
      </MmModal>
    );
  }

  // Completion Screen (Niêm phong biên bản E-5)
  if (isCompleted) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#ecfdf5] text-[#059669] border border-[#a7f3d0]">
          <Award className="h-8 w-8" />
        </div>
        <h1 className="mt-5 font-mm-display text-2xl font-bold text-mm-dark">
          Hoàn Thành Phiên Vấn Đáp Viva!
        </h1>
        <p className="mt-1 text-xs text-[#6b7280]">
          Biên bản câu trả lời của bạn đã được niêm phong kỹ thuật số và chuyển tới hội đồng chấm điểm.
        </p>

        <div className="mt-8 rounded-2xl border border-[#e5e7eb] bg-white p-6 text-left shadow-xs">
          <h3 className="font-semibold text-xs text-mm-dark border-b border-[#f3f4f6] pb-3 uppercase tracking-wider">
            Biên bản kết thúc phiên Viva Sandbox
          </h3>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-xs">
            <div>
              <dt className="text-[#6b7280]">Thí sinh thực hiện:</dt>
              <dd className="mt-0.5 font-bold text-mm-dark">{me?.full_name || "Thí sinh"}</dd>
            </div>
            <div>
              <dt className="text-[#6b7280]">Số câu hỏi đã hoàn tất:</dt>
              <dd className="mt-0.5 font-mono font-bold text-[#059669]">
                {sessionData?.total_questions || 3} / {sessionData?.total_questions || 3} câu
              </dd>
            </div>
            <div>
              <dt className="text-[#6b7280]">Tổng số sự kiện giám sát:</dt>
              <dd className={clsx("mt-0.5 font-mono font-bold", violationLogs.length > 0 ? "text-amber-700" : "text-[#059669]")}>
                {violationLogs.length} lần ghi nhận
              </dd>
            </div>
            <div>
              <dt className="text-[#6b7280]">Trạng thái phiên:</dt>
              <dd className="mt-0.5 font-mono font-bold text-mm-blue-primary">
                SEALED (Đã niêm phong)
              </dd>
            </div>
          </dl>
        </div>

        <div className="mt-8 flex justify-center gap-4">
          <MmButton
            variant="brand"
            size="md"
            onClick={() => navigate(-1)}
            className="rounded-full shadow-sm"
          >
            Quay lại trang chi tiết bài nộp
          </MmButton>
        </div>
      </div>
    );
  }

  const currentIdx = currentQuestion?.question_index || 1;
  const totalQuestions = sessionData?.total_questions || 3;
  const totalDurationMinutes = Math.round((sessionData?.total_duration_seconds || totalQuestions * 300) / 60);
  const progressPercent = Math.round((currentIdx / totalQuestions) * 100);

  return (
    <div className="min-h-screen bg-[#fafbfc]">
      {/* Top Professional Security Bar */}
      <header className="sticky top-0 z-30 border-b border-[#e5e7eb] bg-white/95 backdrop-blur shadow-xs">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Left: Security Tag & Candidate */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-mm-dark text-white">
              <Shield className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mm-display text-sm font-bold text-mm-dark">
                  Phòng Vấn Đáp Viva Sandbox
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-[#ecfdf5] px-2 py-0.5 text-[10px] font-semibold text-[#047857] border border-[#a7f3d0]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#10b981] animate-pulse" />
                  Đang giám sát
                </span>
              </div>
              <span className="text-[11px] text-[#6b7280]">
                Thí sinh: {me?.full_name || "Học viên"} • MSSV: {me?.user_code || "SV2026"}
              </span>
            </div>
          </div>

          {/* Center: Countdown Timer */}
          <div className="flex items-center gap-3">
            <div
              className={clsx(
                "flex items-center gap-1.5 rounded-full px-4 py-1.5 font-mm-mono text-sm font-bold transition-all border",
                remainingSeconds < 120
                  ? "bg-rose-50 text-rose-600 border-rose-300 animate-pulse"
                  : remainingSeconds < 300
                  ? "bg-amber-50 text-amber-700 border-amber-300"
                  : "bg-white text-mm-dark border-[#e5e7eb]"
              )}
            >
              <Clock className="h-4 w-4 text-mm-blue-primary" />
              <span>{formattedTime}</span>
            </div>
          </div>

          {/* Right: Security Violation Detail Button & Progress */}
          <div className="flex items-center gap-3">
            {violationLogs.length > 0 ? (
              <button
                type="button"
                onClick={() => setShowViolationsModal(true)}
                className="flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700 transition-colors hover:bg-rose-100"
                title="Bấm để xem chi tiết các lần ghi nhận vi phạm"
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Vi phạm: {violationLogs.length} (Chi tiết)</span>
              </button>
            ) : (
              <span className="text-xs text-[#059669] font-medium hidden sm:inline">
                Chưa có vi phạm
              </span>
            )}
            <div className="font-mm-mono text-xs font-semibold text-[#4b5563]">
              Câu {currentIdx} / {totalQuestions}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-1 w-full bg-[#f3f4f6]">
          <div
            className="h-1 bg-mm-blue-primary transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </header>

      {/* Main Examination Body */}
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        {/* Window Blur Alert Banner (if user navigated away) */}
        {windowBlurWarning && (
          <div className="mb-6 flex items-start justify-between rounded-xl border border-amber-300 bg-amber-50/90 p-4 text-amber-900 shadow-xs">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-xs">Cảnh báo: Rời cửa sổ làm bài đã được ghi lại!</p>
                <p className="mt-0.5 text-[11px] text-amber-800 leading-relaxed">
                  Hệ thống vừa ghi nhận sự kiện chuyển tab/ứng dụng{lastBlurTimestamp ? ` lúc ${lastBlurTimestamp}` : ""}. Bạn có thể bấm nút &quot;Chi tiết vi phạm&quot; ở góc trên để xem toàn bộ lịch sử.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setWindowBlurWarning(false)}
              className="text-xs font-medium text-amber-900 hover:underline ml-4 flex-shrink-0"
            >
              Đã hiểu
            </button>
          </div>
        )}

        {/* Question Card */}
        {currentQuestion && (
          <div className="mb-6 rounded-2xl border border-[#e5e7eb] bg-white p-6 sm:p-8 shadow-xs">
            <div className="flex items-center justify-between border-b border-[#f3f4f6] pb-3 mb-4">
              <span className="inline-flex items-center gap-1.5 font-mm-ui text-xs font-semibold text-mm-blue-primary uppercase tracking-wider">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Câu hỏi phản biện #{currentIdx}</span>
              </span>
              <span className="text-[11px] text-[#9ca3af] font-mm-mono">
                Tổng thời lượng: {totalDurationMinutes} phút
              </span>
            </div>

            <h2 className="font-mm-display text-lg font-semibold leading-relaxed text-mm-dark sm:text-xl">
              {currentQuestion.question_text}
            </h2>
          </div>
        )}

        {/* Answer Typing Workspace */}
        <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 sm:p-8 shadow-xs">
          <div className="mb-4 flex items-center justify-between">
            <label className="block font-mm-display text-sm font-bold text-mm-dark">
              Câu trả lời của bạn:
            </label>

            {/* Word Count Indicator */}
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  "rounded-full px-3 py-1 font-mm-mono text-xs font-medium transition-colors border",
                  wordCount >= 50
                    ? "bg-[#ecfdf5] text-[#047857] border-[#a7f3d0]"
                    : "bg-gray-50 text-[#6b7280] border-[#e5e7eb]"
                )}
              >
                {wordCount} / 50 từ tối thiểu
              </span>
            </div>
          </div>

          {/* Locked Textarea */}
          <div className={clsx("relative", shakeInput && "animate-shake")}>
            <textarea
              ref={textareaRef}
              rows={8}
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              onPaste={triggerPasteBlock}
              onKeyDown={handleKeyDown}
              onContextMenu={(e) => e.preventDefault()}
              placeholder="Nhập câu trả lời trực tiếp của bạn tại đây... (Thao tác Paste bị khóa; cần tối thiểu 50 từ trước khi nộp)"
              className={clsx(
                "w-full rounded-xl border p-4 font-mm-ui text-sm text-mm-dark leading-relaxed transition-all focus:outline-none focus:ring-2",
                shakeInput
                  ? "border-rose-500 bg-rose-50/20 ring-2 ring-rose-500"
                  : "border-[#e5e7eb] bg-white focus:border-mm-blue-primary focus:ring-mm-blue-primary/20"
              )}
            />
          </div>

          {/* Footer Validation & Submission */}
          <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-[#f3f4f6] pt-4">
            <div className="text-xs text-[#6b7280]">
              {wordCount < 50 ? (
                <span className="text-amber-700">
                  Cần thêm ít nhất {50 - wordCount} từ nữa để gửi câu trả lời.
                </span>
              ) : (
                <span className="text-[#059669] font-medium flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Đã đạt độ dài quy định (&ge; 50 từ).
                </span>
              )}
            </div>

            <MmButton
              variant="brand"
              size="md"
              disabled={wordCount < 50 || submitting}
              loading={submitting}
              onClick={handleSubmitAnswer}
              className="rounded-full shadow-sm"
            >
              <span>{currentIdx < totalQuestions ? "Gửi câu trả lời & Tiếp tục" : "Hoàn tất buổi vấn đáp"}</span>
              <Send className="h-4 w-4 ml-2" />
            </MmButton>
          </div>
        </div>
      </main>

      {/* Violation Details Modal (Minh bạch toàn bộ vi phạm) */}
      <MmModal
        open={showViolationsModal}
        onClose={() => setShowViolationsModal(false)}
        title="Nhật ký giám sát an ninh phòng thi"
        maxWidthClass="max-w-lg"
      >
        <div className="space-y-4 text-xs font-mm-ui text-mm-dark">
          <p className="text-[#6b7280] leading-relaxed">
            Hệ thống tự động lưu vết toàn bộ các sự kiện vi phạm an ninh phòng thi. Danh sách này được gửi kèm biên bản nộp bài để hội đồng khảo thí đối soát.
          </p>

          <div className="max-h-72 overflow-y-auto space-y-2 border border-[#e5e7eb] rounded-xl p-3 bg-[#fafbfc]">
            {violationLogs.length > 0 ? (
              violationLogs.map((log, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-[#e5e7eb] bg-white p-2.5 text-xs shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-rose-700">
                      {log.type === "PASTE_ATTEMPT"
                        ? "Thao tác dán nội dung (Paste Lock)"
                        : log.type === "WINDOW_BLUR"
                        ? "Rời cửa sổ làm bài (Window Blur)"
                        : log.type}
                    </span>
                    <span className="font-mm-mono text-[10px] text-[#9ca3af]">
                      {new Date(log.timestamp).toLocaleTimeString("vi-VN")}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-[#6b7280]">
                    {log.type === "PASTE_ATTEMPT"
                      ? "Cố gắng dán dữ liệu từ Clipboard vào khung trả lời."
                      : "Trình duyệt bị mất tiêu điểm (chuyển sang tab hoặc phần mềm khác)."}
                  </p>
                </div>
              ))
            ) : (
              <p className="py-4 text-center text-xs text-[#9ca3af]">Chưa có vi phạm nào được ghi nhận.</p>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <MmButton variant="secondary" size="sm" onClick={() => setShowViolationsModal(false)}>
              Đóng
            </MmButton>
          </div>
        </div>
      </MmModal>
    </div>
  );
};
