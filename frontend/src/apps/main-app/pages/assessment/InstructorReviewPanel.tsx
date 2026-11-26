/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock,
  FileText,
  GitBranch,
  GraduationCap,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  User,
} from "lucide-react";
import { clsx } from "clsx";

import { assessmentService } from "../../../../services/assessmentService";
import type {
  SubmissionReviewDetailResponse,
  SubmissionReviewSummaryItem,
} from "../../../../types/assessment";
import { MmButton } from "../../components/MmButton";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

interface InstructorReviewPanelProps {
  assignmentId: string;
}

const countWords = (text: string): number => {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
};

export const InstructorReviewPanel: React.FC<InstructorReviewPanelProps> = ({
  assignmentId,
}) => {
  const [submissions, setSubmissions] = useState<SubmissionReviewSummaryItem[]>([]);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reviewDetail, setReviewDetail] =
    useState<SubmissionReviewDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  const loadDetail = useCallback(async (submissionId: string) => {
    try {
      setLoadingDetail(true);
      const detail = await assessmentService.getSubmissionReview(submissionId);
      setReviewDetail(detail);
    } catch (err: any) {
      toast.error(
        resolveErrorMessage(err?.code, "Không thể tải chi tiết đối soát bài nộp.")
      );
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  const loadSubmissions = useCallback(async () => {
    try {
      setLoadingList(true);
      const list = await assessmentService.listAssignmentSubmissions(assignmentId);
      setSubmissions(list);
      if (list.length > 0) {
        const targetId =
          selectedId && list.some((item) => item.id === selectedId)
            ? selectedId
            : list[0].id;
        setSelectedId(targetId);
        void loadDetail(targetId);
      } else {
        setSelectedId(null);
        setReviewDetail(null);
      }
    } catch (err: any) {
      toast.error(
        resolveErrorMessage(err?.code, "Không thể tải danh sách bài nộp của lớp.")
      );
    } finally {
      setLoadingList(false);
    }
  }, [assignmentId, loadDetail, selectedId]);

  useEffect(() => {
    void loadSubmissions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignmentId]);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    void loadDetail(id);
  };

  if (loadingList) {
    return (
      <div className="flex min-h-[260px] items-center justify-center rounded-2xl border border-[#e5e7eb] bg-white p-8">
        <div className="flex items-center gap-3 text-sm text-[#6b7280]">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-mm-blue-primary border-t-transparent" />
          <span>Đang tải danh sách bài nộp sinh viên...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left 4 cols: Student Submissions List */}
      <div className="lg:col-span-4 space-y-4">
        <div className="rounded-2xl border border-[#e5e7eb] bg-white p-5 shadow-xs">
          <div className="mb-4 flex items-center justify-between border-b border-[#f3f4f6] pb-3">
            <div>
              <h2 className="font-mm-display text-sm font-bold text-mm-dark">
                Bài nộp Sinh viên ({submissions.length})
              </h2>
              <p className="text-[11px] text-[#6b7280]">
                Chọn bài nộp để xem tóm tắt AI và biên bản Viva
              </p>
            </div>
            <MmButton
              variant="secondary"
              size="sm"
              onClick={() => void loadSubmissions()}
              title="Làm mới danh sách"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </MmButton>
          </div>

          {submissions.length === 0 ? (
            <div className="py-10 text-center text-xs text-[#9ca3af]">
              Chưa có sinh viên nào nộp bài cho bài tập này.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[680px] overflow-y-auto pr-1">
              {submissions.map((item) => {
                const isActive = selectedId === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelect(item.id)}
                    className={clsx(
                      "w-full rounded-xl border p-3.5 text-left transition-all",
                      isActive
                        ? "border-mm-blue-primary bg-[#eff6ff]/60 shadow-xs"
                        : "border-[#e5e7eb] bg-white hover:border-gray-300"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mm-display text-xs font-bold text-mm-dark truncate">
                        {item.student_name}
                      </span>
                      <span className="rounded-full border border-[#e5e7eb] bg-white px-2 py-0.5 font-mm-mono text-[10px] font-semibold text-[#374151]">
                        v{item.version}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] text-[#6b7280] truncate">
                      {item.student_email}
                    </p>
                    {item.project_title && (
                      <p className="mt-1.5 text-xs font-medium text-mm-dark line-clamp-1">
                        {item.project_title}
                      </p>
                    )}

                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[10px]">
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 font-medium",
                          item.status === "VIVA_COMPLETED" ||
                            item.status === "GRADED"
                            ? "bg-[#ecfdf5] text-[#047857]"
                            : "bg-amber-50 text-amber-800"
                        )}
                      >
                        {item.status}
                      </span>
                      {item.has_ai_digest && (
                        <span className="rounded-full bg-[#eff6ff] px-2 py-0.5 font-medium text-[#1e40af]">
                          Có tóm tắt AI
                        </span>
                      )}
                      {item.violation_count > 0 && (
                        <span className="rounded-full bg-rose-50 px-2 py-0.5 font-semibold text-rose-700">
                          {item.violation_count} vi phạm
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right 8 cols: Full Inspection View */}
      <div className="lg:col-span-8 space-y-6">
        {loadingDetail ? (
          <div className="flex min-h-[260px] items-center justify-center rounded-2xl border border-[#e5e7eb] bg-white p-8">
            <div className="flex items-center gap-3 text-sm text-[#6b7280]">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-mm-blue-primary border-t-transparent" />
              <span>Đang tải bản tóm tắt và biên bản Viva...</span>
            </div>
          </div>
        ) : !reviewDetail ? (
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-10 text-center text-sm text-[#6b7280]">
            Chọn một bài nộp bên trái để kiểm tra bản tóm tắt, câu hỏi Viva và câu trả lời của sinh viên.
          </div>
        ) : (
          <>
            {/* Card 1: Submission & AI Disclosure Overview */}
            <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#f3f4f6] pb-4">
                <div>
                  <div className="flex items-center gap-2 text-xs text-[#6b7280]">
                    <User className="h-3.5 w-3.5 text-mm-blue-primary" />
                    <span className="font-semibold text-mm-dark">
                      {reviewDetail.student_name}
                    </span>
                    <span>({reviewDetail.student_email})</span>
                  </div>
                  <h3 className="mt-1 font-mm-display text-lg font-bold text-mm-dark">
                    {reviewDetail.project_title || reviewDetail.assignment_title}
                  </h3>
                  <p className="mt-0.5 font-mm-mono text-[11px] text-[#6b7280]">
                    Phiên bản v{reviewDetail.version} · Nộp lúc{" "}
                    {new Date(reviewDetail.submitted_at).toLocaleString("vi-VN")}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <Link
                    to={`/courses/${reviewDetail.course_id}/assignments/${reviewDetail.assignment_id}/speedgrader?submissionId=${reviewDetail.submission_id}`}
                    className="inline-flex items-center gap-1.5 rounded-full bg-mm-blue-primary px-3 py-1 font-semibold text-white hover:opacity-95 transition-opacity"
                  >
                    <GraduationCap className="h-3.5 w-3.5" />
                    Mở SpeedGrader 3 Cột
                  </Link>
                  <span className="rounded-full border border-[#e5e7eb] bg-[#f9fafb] px-3 py-1 font-medium text-mm-dark">
                    Tự thực hiện: {reviewDetail.self_contribution_pct}%
                  </span>
                  <span
                    className={clsx(
                      "rounded-full border px-3 py-1 font-medium",
                      reviewDetail.is_late
                        ? "border-rose-200 bg-rose-50 text-rose-700"
                        : "border-[#a7f3d0] bg-[#ecfdf5] text-[#047857]"
                    )}
                  >
                    {reviewDetail.is_late
                      ? `Trễ hạn (-${reviewDetail.late_penalty_applied}%)`
                      : "Đúng hạn"}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 text-xs">
                <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3.5 space-y-1.5">
                  <span className="font-semibold text-mm-dark flex items-center gap-1.5">
                    {reviewDetail.git_repo_url ? (
                      <GitBranch className="h-3.5 w-3.5 text-mm-blue-primary" />
                    ) : (
                      <FileText className="h-3.5 w-3.5 text-mm-blue-primary" />
                    )}
                    <span>Nguồn bài nộp</span>
                  </span>
                  {reviewDetail.git_repo_url ? (
                    <a
                      href={reviewDetail.git_repo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-mm-blue-primary hover:underline font-mm-mono"
                    >
                      {reviewDetail.git_repo_url}
                    </a>
                  ) : (
                    <p className="truncate font-mm-mono text-[#4b5563]">
                      {reviewDetail.file_url || "Không có tệp đính kèm"}
                    </p>
                  )}
                </div>

                <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3.5 space-y-1.5">
                  <span className="font-semibold text-mm-dark flex items-center gap-1.5">
                    <Bot className="h-3.5 w-3.5 text-mm-blue-primary" />
                    <span>Khai báo công cụ AI</span>
                  </span>
                  <p className="text-[#4b5563]">
                    Công cụ:{" "}
                    <span className="font-medium text-mm-dark">
                      {reviewDetail.ai_disclosure_data?.tools_used?.length
                        ? reviewDetail.ai_disclosure_data.tools_used.join(", ")
                        : "Không khai báo"}
                    </span>
                  </p>
                  <p className="text-[#4b5563] line-clamp-2">
                    {reviewDetail.ai_disclosure_data?.usage_description ||
                      "Không có mô tả thêm."}
                  </p>
                </div>
              </div>
            </div>

            {/* Card 2: Saved AI Digest Summary (Call 1) */}
            <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f3f4f6] pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-mm-blue-primary" />
                  <h3 className="font-mm-display text-base font-bold text-mm-dark">
                    Bản tóm tắt nội dung bài nộp (Call 1 — Lưu từ CSDL)
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mm-mono">
                  {reviewDetail.digest_type && (
                    <span className="rounded-full bg-[#eff6ff] px-2.5 py-0.5 font-semibold text-[#1e40af]">
                      {reviewDetail.digest_type}
                    </span>
                  )}
                  {reviewDetail.summarizer_mode && (
                    <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[#4b5563]">
                      {reviewDetail.summarizer_mode}
                    </span>
                  )}
                  {reviewDetail.generation_source && (
                    <span className="rounded-full bg-[#ecfdf5] px-2.5 py-0.5 text-[#047857]">
                      {reviewDetail.generation_source}
                    </span>
                  )}
                </div>
              </div>

              {reviewDetail.ai_digest_summary ? (
                <div className="prose prose-sm max-w-none rounded-xl border border-[#f3f4f6] bg-[#fafafa] p-4 text-[#1f2937]">
                  <MarkdownRenderer content={reviewDetail.ai_digest_summary} />
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-[#d1d5db] bg-[#f9fafb] p-4 text-xs text-[#6b7280]">
                  Bài nộp này chưa có bản tóm tắt AI được lưu trong CSDL (có thể là bản nộp cũ trước khi kích hoạt lưu digest, hoặc bài tập không bật chế độ sinh Viva).
                </div>
              )}
            </div>

            {/* Card 3: Viva Questions (Call 2) & Student Answers */}
            <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f3f4f6] pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#047857]" />
                  <h3 className="font-mm-display text-base font-bold text-mm-dark">
                    Biên bản Vấn đáp Viva ({reviewDetail.questions.length} câu hỏi)
                  </h3>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="rounded-full bg-gray-100 px-2.5 py-0.5 font-mm-mono font-medium text-mm-dark">
                    Trạng thái Viva: {reviewDetail.viva_status || "CHƯA KHỞI TẠO"}
                  </span>
                </div>
              </div>

              {reviewDetail.questions.length === 0 ? (
                <p className="text-xs text-[#6b7280]">
                  Chưa có câu hỏi Viva nào được ghi nhận cho bài nộp này.
                </p>
              ) : (
                <div className="space-y-4">
                  {reviewDetail.questions.map((q) => {
                    const ans = reviewDetail.answers[q.id];
                    const words = ans?.answer_text
                      ? countWords(ans.answer_text)
                      : 0;
                    return (
                      <div
                        key={q.id}
                        className="rounded-xl border border-[#e5e7eb] bg-white p-4 space-y-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-mm-mono text-xs font-bold text-mm-blue-primary">
                            Câu {q.question_index} / {reviewDetail.total_questions || reviewDetail.questions.length} ({q.category})
                          </span>
                          {ans && (
                            <div className="flex items-center gap-2 text-[11px] text-[#6b7280]">
                              <span>{words} từ</span>
                              {typeof ans.time_spent_seconds === "number" && (
                                <span className="inline-flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {ans.time_spent_seconds}s
                                </span>
                              )}
                              {ans.auto_saved_on_timeout && (
                                <span className="rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-800">
                                  Tự lưu khi hết giờ
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        <p className="text-sm font-semibold text-mm-dark leading-relaxed">
                          {q.question_text}
                        </p>

                        <div className="rounded-lg border border-[#f3f4f6] bg-[#f9fafb] p-3 text-xs text-[#374151] whitespace-pre-wrap leading-relaxed">
                          {ans?.answer_text ? (
                            ans.answer_text
                          ) : (
                            <span className="italic text-[#9ca3af]">
                              Sinh viên chưa gửi câu trả lời cho câu hỏi này.
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Card 4: Integrity Violation Logs & Grading Guidance */}
            <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#f3f4f6] pb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-rose-600" />
                  <h3 className="font-mm-display text-base font-bold text-mm-dark">
                    Nhật ký Liêm chính & Căn cứ Chấm điểm ({reviewDetail.violation_logs.length} cảnh báo)
                  </h3>
                </div>
              </div>

              {reviewDetail.violation_logs.length > 0 ? (
                <div className="space-y-2">
                  {reviewDetail.violation_logs.map((log, idx) => (
                    <div
                      key={`${log.type}-${idx}`}
                      className="flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
                    >
                      <span className="inline-flex items-center gap-1.5 font-semibold">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        {log.type}
                      </span>
                      <span className="font-mm-mono text-[11px]">
                        {log.timestamp
                          ? new Date(log.timestamp).toLocaleString("vi-VN")
                          : ""}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[#047857]">
                  Không phát hiện hành vi rời màn hình (Window Blur) hay cố tình dán văn bản (Paste Attempt).
                </p>
              )}

              <div className="rounded-xl border border-[#dbeafe] bg-[#eff6ff]/70 p-3.5 text-xs text-[#1e3a8a] leading-relaxed">
                <strong>Quy tắc chấm điểm (Human-in-the-Loop BR-07):</strong> Bản tóm tắt AI, biên bản hỏi-đáp Viva, khai báo AI và nhật ký vi phạm ở trên là bộ hồ sơ bằng chứng đầu vào cho <strong>Rubric & SpeedGrader (Module Gradebook)</strong>. AI chỉ đề xuất điểm tham khảo ở trạng thái <code>AI_PROPOSED</code> kèm trích dẫn và cảnh báo mâu thuẫn (<code>CONFLICTING</code>); <strong>Giảng viên là người đọc lại đối chiếu và chốt điểm chính thức</strong>.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
