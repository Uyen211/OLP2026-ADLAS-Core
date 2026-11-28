// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Flag,
  Send,
  AlertTriangle,
} from "lucide-react";
import {
  DotGridCanvas,
  EduButton,
  EduCard,
  EduConfirmDialog,
} from "../../../../design-system";
import { StrictModeBanner } from "../components/StrictModeBanner";
import { AutosaveStatusPill } from "../components/AutosaveStatusPill";
import { ExamQuestionNavigator } from "../components/ExamQuestionNavigator";
import { AlertTimelineDrawer } from "../components/AlertTimelineDrawer";
import { useExamAutosave2Tier } from "../hooks/useExamAutosave2Tier";
import { useStrictExamGuard } from "../hooks/useStrictExamGuard";
import { examinationService } from "../../../../services/examinationService";
import type {
  AttemptStartResponse,
  AttemptQuestionResponse,
} from "../../../../types/examination";

export const StrictExamTakingPage: React.FC = () => {
  const { courseId, quizId } = useParams<{ courseId: string; quizId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<AttemptStartResponse | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [confirmSubmitOpen, setConfirmSubmitOpen] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  // Khởi động hoặc tiếp tục phiên làm bài
  useEffect(() => {
    if (!quizId) return;
    setLoading(true);
    examinationService
      .startOrResumeAttempt(quizId)
      .then((sess) => {
        setSession(sess);
      })
      .catch(() => {
        // Không thể vào bài thi
      })
      .finally(() => {
        setLoading(false);
      });
  }, [quizId]);

  const questions: AttemptQuestionResponse[] = session?.questions || [];
  const submissionId = session?.submission_id || "";
  const isStrictProctored = session?.security_mode === "REMOTE_PROCTORED";

  // Tier 2 Autosave Hook
  const {
    answers,
    flaggedQuestions,
    syncStatus,
    lastSavedAt,
    updateAnswer,
    toggleFlagQuestion,
  } = useExamAutosave2Tier({
    submissionId,
    quizId: quizId || "",
    initialSeqNum: session?.seq_num || 0,
    initialAnswers: session?.student_answers || {},
  });

  // Strict Exam Guard Hook
  const {
    strikes,
    violations,
    isFullscreen,
    isWarningActive,
    activeWarningText,
    dismissWarning,
    requestFullscreen,
  } = useStrictExamGuard({
    submissionId,
    isStrictMode: isStrictProctored,
  });

  const currentQ = questions[currentQuestionIndex];
  const answeredQuestionIds = useMemo(
    () => Object.keys(answers).filter((qid) => answers[qid]?.length > 0),
    [answers]
  );
  const questionIds = useMemo(() => questions.map((q) => q.id), [questions]);

  // Nộp bài thi
  const handleSubmitExam = async () => {
    if (!submissionId) return;
    setIsSubmitting(true);
    try {
      await examinationService.submitAttempt(submissionId);
      navigate(`/courses/${courseId}/exams/${quizId}/result`);
    } catch {
      // Non-blocking
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5fbfd]">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 rounded-full border-2 border-[#006699] border-t-transparent animate-spin mx-auto" />
          <p className="text-xs font-semibold text-[#4a5f75]">Đang khởi tạo phòng thi...</p>
        </div>
      </div>
    );
  }

  return (
    <DotGridCanvas className="min-h-screen flex flex-col bg-[#f5fbfd]">
      {/* Strict Mode Top Banner */}
      <StrictModeBanner
        strikes={strikes}
        maxStrikes={3}
        isFullscreen={isFullscreen}
        onRequestFullscreen={requestFullscreen}
      />

      {/* Warning Overlay Modal khi vi phạm */}
      {isWarningActive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-white shadow-2xl border-2 border-[#be123c] space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-3 text-[#be123c]">
              <AlertTriangle className="w-7 h-7 shrink-0" />
              <h3 className="text-base font-bold">Cảnh báo Giám sát Phòng thi!</h3>
            </div>
            <p className="text-xs text-[#0f2236] leading-relaxed">
              {activeWarningText}
            </p>
            <p className="text-[11px] text-[#4a5f75]">
              Mọi hành động rời khỏi màn hình hoặc phím tắt đều được hệ thống ghi lại trong nhật ký giám sát. Quá 3 lần vi phạm, bài thi sẽ bị đánh dấu xem xét kỷ luật.
            </p>
            <div className="flex justify-end pt-2">
              <EduButton variant="primary" onClick={dismissWarning}>
                Tôi đã hiểu và tiếp tục làm bài
              </EduButton>
            </div>
          </div>
        </div>
      )}

      {/* Top Header Navigation */}
      <header className="px-4 py-3 bg-white border-b border-[rgba(15,34,54,0.08)] flex items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold text-[#4a5f75] uppercase block">
            Bài thi trực tuyến
          </span>
          <h1 className="text-base font-bold text-[#0f2236]">
            Phòng thi Giám sát Nghiêm ngặt
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <AutosaveStatusPill status={syncStatus} lastSavedAt={lastSavedAt} />

          {violations.length > 0 && (
            <button
              type="button"
              onClick={() => setTimelineOpen(true)}
              className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#fff1f2] text-[#be123c] border border-[#fecdd3] hover:bg-[#ffe4e6]"
            >
              Xem {violations.length} cảnh báo
            </button>
          )}

          <EduButton
            variant="primary"
            onClick={() => setConfirmSubmitOpen(true)}
          >
            <Send className="w-3.5 h-3.5 mr-1.5" />
            <span>Nộp bài thi</span>
          </EduButton>
        </div>
      </header>

      {/* Main Examination Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Cột trái: Nội dung câu hỏi */}
        <section className="lg:col-span-8 space-y-4">
          {currentQ ? (
            <EduCard variant="surface" padding="lg" className="border border-[rgba(15,34,54,0.12)] space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-[rgba(15,34,54,0.08)]">
                <span className="text-xs font-bold text-[#006699] uppercase tracking-wider">
                  Câu hỏi {currentQuestionIndex + 1} / {questions.length}
                </span>

                <button
                  type="button"
                  onClick={() => toggleFlagQuestion(currentQ.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    flaggedQuestions.includes(currentQ.id)
                      ? "bg-[#fffbeb] text-[#b45309] border border-[#fde68a]"
                      : "bg-[#f5fbfd] text-[#4a5f75] hover:text-[#0f2236]"
                  }`}
                >
                  <Flag className="w-3.5 h-3.5" />
                  <span>
                    {flaggedQuestions.includes(currentQ.id) ? "Đã gắn cờ" : "Gắn cờ xem lại"}
                  </span>
                </button>
              </div>

              {/* Nội dung đề bài */}
              <div className="text-base font-semibold text-[#0f2236] leading-relaxed">
                {currentQ.question_text}
              </div>

              {/* Danh sách phương án trả lời */}
              <div className="space-y-3 pt-2">
                {currentQ.options_snapshot?.map((opt) => {
                  const currentSelected = answers[currentQ.id] || [];
                  const isSelected = Array.isArray(currentSelected)
                    ? currentSelected.includes(opt.key)
                    : currentSelected === opt.key;

                  return (
                    <div
                      key={opt.key}
                      onClick={() => updateAnswer(currentQ.id, [opt.key])}
                      className={`p-3.5 rounded-xl border-2 flex items-center gap-3 cursor-pointer transition-all ${
                        isSelected
                          ? "border-[#006699] bg-[#eaf6fa] shadow-sm font-semibold"
                          : "border-[rgba(15,34,54,0.1)] bg-white hover:border-[rgba(15,34,54,0.25)] hover:bg-[#f5fbfd]"
                      }`}
                    >
                      <div
                        className={`w-7 h-7 rounded-full text-xs font-mono font-bold flex items-center justify-center shrink-0 transition-colors ${
                          isSelected
                            ? "bg-[#006699] text-white"
                            : "bg-[#f5fbfd] border border-[rgba(15,34,54,0.15)] text-[#0f2236]"
                        }`}
                      >
                        {isSelected ? <CheckCircle2 className="w-4 h-4" /> : opt.key}
                      </div>
                      <span className="text-sm text-[#0f2236] flex-1">{opt.text}</span>
                    </div>
                  );
                })}
              </div>

              {/* Nút điều hướng trước / sau */}
              <div className="flex justify-between items-center pt-4 border-t border-[rgba(15,34,54,0.08)]">
                <EduButton
                  variant="secondary"
                  disabled={currentQuestionIndex === 0}
                  onClick={() => setCurrentQuestionIndex((prev) => Math.max(0, prev - 1))}
                >
                  <ArrowLeft className="w-4 h-4 mr-1.5" />
                  <span>Câu trước</span>
                </EduButton>

                <EduButton
                  variant="secondary"
                  disabled={currentQuestionIndex === questions.length - 1}
                  onClick={() =>
                    setCurrentQuestionIndex((prev) => Math.min(questions.length - 1, prev + 1))
                  }
                >
                  <span>Câu tiếp theo</span>
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </EduButton>
              </div>
            </EduCard>
          ) : (
            <div className="p-12 text-center text-sm text-[#4a5f75]">
              Không có câu hỏi trong bài thi này.
            </div>
          )}
        </section>

        {/* Cột phải: Bảng điều hướng câu hỏi */}
        <aside className="lg:col-span-4 space-y-4">
          <ExamQuestionNavigator
            totalQuestions={questions.length}
            currentIndex={currentQuestionIndex}
            answeredQuestionIds={answeredQuestionIds}
            flaggedQuestionIds={flaggedQuestions}
            questionIds={questionIds}
            onSelectQuestion={setCurrentQuestionIndex}
          />
        </aside>
      </main>

      {/* Drawer xem nhật ký cảnh báo */}
      <AlertTimelineDrawer
        isOpen={timelineOpen}
        onClose={() => setTimelineOpen(false)}
        violations={violations}
      />

      {/* Xác nhận nộp bài */}
      <EduConfirmDialog
        isOpen={confirmSubmitOpen}
        onClose={() => setConfirmSubmitOpen(false)}
        onConfirm={handleSubmitExam}
        title="Xác nhận Nộp bài thi"
        message={`Bạn đã hoàn thành ${answeredQuestionIds.length}/${questions.length} câu hỏi. Bạn có chắc chắn muốn nộp bài thi ngay bây giờ?`}
        confirmLabel={isSubmitting ? "Đang nộp..." : "Xác nhận nộp bài"}
        cancelLabel="Tiếp tục làm bài"
      />
    </DotGridCanvas>
  );
};
