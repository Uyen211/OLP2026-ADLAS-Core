/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Award,
  CheckCircle2,
  Clock,
  FileCheck2,
  Lock,
  MessageSquareWarning,
  XCircle,
} from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type {
  AttemptResultResponse,
  RegradeSummaryResponse,
  ResultQuestionAnalysis,
} from "../../../../types/examination";
import { MathCodeContent } from "../../components/MathCodeContent";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { showToast } from "../../components/Toast";
import { StudentLayout } from "../../layouts/StudentLayout";
import {
  formatCountdown,
  formatDateTime,
  formatScore,
  getLastSubmissionStorageKey,
  GRADE_RELEASE_LABELS,
  QUESTION_TYPE_LABELS,
  REGRADE_STATUS_META,
  toNumeric,
} from "./examHelpers";
import { RegradeSubmitModal } from "./RegradeSubmitModal";

export const ExamResultPage: React.FC = () => {
  const { courseId = "", quizId = "" } = useParams<{
    courseId: string;
    quizId: string;
  }>();
  const [searchParams] = useSearchParams();

  const submissionId =
    searchParams.get("submissionId") ||
    (quizId ? localStorage.getItem(getLastSubmissionStorageKey(quizId)) : null) ||
    "";

  const [result, setResult] = useState<AttemptResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [regradeRemainingSec, setRegradeRemainingSec] = useState<number>(0);
  const [regradeTarget, setRegradeTarget] =
    useState<ResultQuestionAnalysis | null>(null);

  const loadResult = useCallback(async () => {
    if (!submissionId) {
      setLoading(false);
      setErrorMsg("Không tìm thấy mã bài nộp để tra cứu kết quả.");
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await examinationService.getAttemptResult(submissionId);
      setResult(data);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Không thể tải kết quả bài thi.";
      setErrorMsg(message);
      showToast("error", message);
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    void loadResult();
  }, [loadResult]);

  // 48-hour regrade countdown timer
  useEffect(() => {
    if (!result?.regrade_deadline) {
      setRegradeRemainingSec(0);
      return;
    }
    const deadlineMs = new Date(result.regrade_deadline).getTime();
    const updateRemaining = () => {
      const diff = Math.max(0, Math.floor((deadlineMs - Date.now()) / 1000));
      setRegradeRemainingSec(diff);
    };
    updateRemaining();
    const timer = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timer);
  }, [result?.regrade_deadline]);

  const regradeByQuestionId = useMemo(() => {
    const map = new Map<string, RegradeSummaryResponse>();
    result?.regrades.forEach((rg) => {
      if (rg.attempt_question_id) {
        map.set(rg.attempt_question_id, rg);
      }
    });
    return map;
  }, [result?.regrades]);

  const isRegradeOpen = Boolean(
    result?.can_request_regrade && regradeRemainingSec > 0
  );

  const correctCount = useMemo(
    () => result?.questions.filter((q) => q.is_correct).length ?? 0,
    [result?.questions]
  );

  return (
    <StudentLayout>
      <div className="space-y-6">
        <Link
          to={`/courses/${courseId}/exams`}
          className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Quay lại danh sách kỳ thi</span>
        </Link>

        {loading ? (
          <div className="space-y-4">
            <div className="h-32 animate-pulse rounded-mm-card bg-mm-divider/60" />
            <div className="h-64 animate-pulse rounded-mm-card bg-mm-divider/40" />
          </div>
        ) : errorMsg || !result ? (
          <MmCard variant="standard" className="py-12 text-center">
            <AlertCircle className="mx-auto mb-3 h-10 w-10 text-mm-danger" />
            <p className="font-mm-ui text-base text-mm-heading">
              {errorMsg || "Không tìm thấy kết quả bài thi."}
            </p>
          </MmCard>
        ) : !result.grades_visible ? (
          <MmCard variant="ambient" radius="card-lg" padding="lg">
            <div className="mx-auto max-w-lg py-6 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-mm-blue-light/30 text-mm-blue-hover">
                <Lock className="h-7 w-7" />
              </div>
              <h1 className="font-mm-display text-[26px] font-semibold tracking-tight text-mm-heading">
                Đã ghi nhận bài làm của bạn
              </h1>
              <p className="mt-2 font-mm-ui text-sm text-mm-text-secondary">
                Kỳ thi <span className="font-medium text-mm-heading">{result.quiz_title}</span>{" "}
                đã được nộp thành công lúc {formatDateTime(result.submitted_at)}.
              </p>

              <div className="mt-5 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-4 font-mm-ui text-sm text-mm-text-secondary">
                <p className="font-medium text-mm-heading">
                  Điểm số và lời giải hiện đang chờ công bố
                </p>
                <p className="mt-1 text-xs">
                  Chính sách kỳ thi: {GRADE_RELEASE_LABELS[result.grade_release_policy]}.
                  {result.release_timestamp &&
                    ` Thời điểm dự kiến mở điểm: ${formatDateTime(result.release_timestamp)}.`}
                </p>
              </div>
            </div>
          </MmCard>
        ) : (
          <>
            {/* Score Summary Card */}
            <MmCard variant="ambient" radius="card-lg" padding="lg">
              <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-mm-success-bg px-3 py-0.5 font-mm-ui text-xs font-medium text-mm-success">
                    <Award className="h-3.5 w-3.5" />
                    <span>Kết quả đã công bố</span>
                  </div>
                  <h1 className="font-mm-display text-[28px] font-semibold tracking-tight text-mm-heading">
                    {result.quiz_title}
                  </h1>
                  <p className="font-mm-ui text-xs text-mm-text-secondary">
                    Nộp bài lúc: {formatDateTime(result.submitted_at)} · Trả lời đúng hoàn toàn:{" "}
                    {correctCount}/{result.questions.length} câu
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-4">
                  <div className="rounded-mm-card border border-mm-blue-hover/25 bg-mm-blue-light/15 px-6 py-4 text-center">
                    <p className="font-mm-ui text-xs text-mm-text-secondary">
                      Tổng điểm (thang 10.0)
                    </p>
                    <p className="mt-1 font-mm-mono text-4xl font-medium text-mm-blue-hover">
                      {formatScore(result.final_score ?? result.auto_score)}
                      <span className="text-lg text-mm-text-muted"> / 10.0</span>
                    </p>
                  </div>

                  {/* 48h Regrade Window Box */}
                  <div
                    className={`rounded-mm-card border px-5 py-4 ${
                      isRegradeOpen
                        ? "border-mm-warning/40 bg-mm-warning-bg/70 text-mm-warning"
                        : "border-mm-border bg-mm-divider/40 text-mm-text-muted"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-mm-ui text-xs font-medium">
                      <Clock className="h-3.5 w-3.5" />
                      <span>Cửa sổ phúc khảo 48 giờ</span>
                    </div>
                    {isRegradeOpen ? (
                      <>
                        <p className="mt-1 font-mm-mono text-xl font-medium text-mm-heading">
                          {formatCountdown(regradeRemainingSec)}
                        </p>
                        <p className="mt-0.5 font-mm-ui text-[11px]">
                          Hạn chót: {formatDateTime(result.regrade_deadline)}
                        </p>
                      </>
                    ) : (
                      <p className="mt-1 font-mm-ui text-xs">
                        [E-REG-01] Đã hết thời hạn 48 giờ gửi đơn phúc khảo.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </MmCard>

            {/* Per-Question Breakdown */}
            <div className="space-y-4">
              <h2 className="font-mm-mid text-xl font-medium text-mm-heading">
                Phân tích chi tiết từng câu hỏi
              </h2>

              {result.questions.map((q) => {
                const existingRegrade = regradeByQuestionId.get(q.attempt_question_id);
                return (
                  <MmCard
                    key={q.attempt_question_id}
                    variant="standard"
                    radius="card"
                    padding="lg"
                  >
                    <div className="flex flex-col justify-between gap-3 border-b border-mm-divider pb-3 sm:flex-row sm:items-center">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-mm-dark px-3 py-0.5 font-mm-mono text-xs font-medium text-white">
                          Câu {q.question_order}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mm-ui text-xs font-medium ${
                            q.is_correct
                              ? "bg-mm-success-bg text-mm-success"
                              : "bg-mm-danger-bg text-mm-danger"
                          }`}
                        >
                          {q.is_correct ? (
                            <>
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              <span>Chính xác</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="h-3.5 w-3.5" />
                              <span>Chưa chính xác</span>
                            </>
                          )}
                        </span>
                        <span className="rounded-mm-tag bg-mm-divider px-2 py-0.5 font-mm-ui text-xs text-mm-text-secondary">
                          {QUESTION_TYPE_LABELS[q.question_type]}
                        </span>
                        <span className="font-mm-data text-xs text-mm-text-muted">
                          Điểm đạt: {toNumeric(q.earned_points).toFixed(2)} /{" "}
                          {toNumeric(q.default_points).toFixed(2)}
                        </span>
                      </div>

                      {existingRegrade ? (
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 font-mm-ui text-xs font-medium ${
                            REGRADE_STATUS_META[existingRegrade.status].className
                          }`}
                        >
                          <FileCheck2 className="h-3.5 w-3.5" />
                          <span>
                            Phúc khảo:{" "}
                            {REGRADE_STATUS_META[existingRegrade.status].label}
                          </span>
                        </span>
                      ) : (
                        <MmButton
                          variant="secondary"
                          size="sm"
                          disabled={!isRegradeOpen}
                          title={
                            isRegradeOpen
                              ? "Gửi đơn phúc khảo câu hỏi này"
                              : "Đã quá thời hạn 48 giờ phúc khảo (E-REG-01)"
                          }
                          onClick={() => setRegradeTarget(q)}
                        >
                          <MessageSquareWarning className="h-3.5 w-3.5" />
                          <span>
                            {isRegradeOpen
                              ? "Gửi đơn phúc khảo"
                              : "Quá hạn phúc khảo (E-REG-01)"}
                          </span>
                        </MmButton>
                      )}
                    </div>

                    <div className="mt-4">
                      <MathCodeContent
                        content={q.question_text}
                        className="text-sm text-mm-heading"
                      />
                    </div>

                    <div className="mt-4 space-y-2">
                      {q.options_snapshot.map((opt) => {
                        const isSelected = q.selected_keys.includes(opt.key);
                        const isCorrectOpt = q.correct_keys.includes(opt.key);

                        let rowClass =
                          "border-mm-divider bg-mm-bg text-mm-text-secondary";
                        let textExtraClass = "";

                        if (isCorrectOpt) {
                          rowClass =
                            "border-mm-success/40 bg-mm-success-bg/60 text-mm-success";
                        } else if (isSelected && !isCorrectOpt) {
                          rowClass =
                            "border-mm-danger/40 bg-mm-danger-bg/70 text-mm-danger";
                          textExtraClass = "line-through";
                        }

                        return (
                          <div
                            key={opt.key}
                            className={`flex items-start justify-between gap-3 rounded-mm-panel border px-3.5 py-2.5 text-sm ${rowClass}`}
                          >
                            <div className="flex items-start gap-2.5">
                              <span className="font-mm-mono text-xs font-medium">
                                {opt.key}.
                              </span>
                              <MathCodeContent
                                content={opt.text}
                                inline
                                className={`text-sm text-inherit ${textExtraClass}`}
                              />
                            </div>

                            <div className="flex shrink-0 items-center gap-1.5 font-mm-ui text-xs">
                              {isSelected && (
                                <span className="rounded-mm-tag bg-white/80 px-2 py-0.5 text-mm-heading">
                                  Bạn chọn
                                </span>
                              )}
                              {isCorrectOpt && (
                                <span className="rounded-mm-tag bg-mm-success px-2 py-0.5 text-white">
                                  Đáp án đúng
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {q.explanation_snapshot && (
                      <div className="mt-4 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3.5">
                        <p className="mb-1 font-mm-ui text-xs font-medium text-mm-text-muted">
                          Lời giải thích
                        </p>
                        <MathCodeContent
                          content={q.explanation_snapshot}
                          className="text-sm text-mm-text-secondary"
                        />
                      </div>
                    )}

                    {existingRegrade?.reviewer_feedback && (
                      <div className="mt-3 rounded-mm-panel border border-mm-blue-hover/25 bg-mm-blue-light/15 p-3.5">
                        <p className="font-mm-ui text-xs font-medium text-mm-blue-hover">
                          Phản hồi phúc khảo từ Giảng viên
                        </p>
                        <p className="mt-1 font-mm-ui text-sm text-mm-heading">
                          {existingRegrade.reviewer_feedback}
                        </p>
                      </div>
                    )}
                  </MmCard>
                );
              })}
            </div>
          </>
        )}
      </div>

      {result && (
        <RegradeSubmitModal
          open={Boolean(regradeTarget)}
          submissionId={result.submission_id}
          question={regradeTarget}
          onClose={() => setRegradeTarget(null)}
          onSubmitted={() => void loadResult()}
        />
      )}
    </StudentLayout>
  );
};
