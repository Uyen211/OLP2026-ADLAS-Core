/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  GitBranch,
  History,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { clsx } from "clsx";

import { assessmentService } from "../../../../services/assessmentService";
import type { AssignmentDetail, Submission } from "../../../../types/assessment";
import { MmButton } from "../../components/MmButton";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";
import { PillTabs } from "../../components/PillTabs";
import { toast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

const AI_TOOL_OPTIONS = [
  { id: "chatgpt", label: "ChatGPT (OpenAI)" },
  { id: "claude", label: "Claude (Anthropic)" },
  { id: "copilot", label: "GitHub Copilot" },
  { id: "gemini", label: "Google Gemini" },
  { id: "cursor", label: "Cursor AI" },
  { id: "other", label: "Công cụ khác" },
];

export const AssignmentDetailPage: React.FC = () => {
  const { courseId, assignmentId } = useParams<{ courseId: string; assignmentId: string }>();
  const navigate = useNavigate();

  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Form State
  const [projectTitle, setProjectTitle] = useState<string>("");
  const [submissionTab, setSubmissionTab] = useState<string>("file"); // "file" | "git"
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gitRepoUrl, setGitRepoUrl] = useState<string>("");
  const [studentComments, setStudentComments] = useState<string>("");

  // AI Disclosure Form State
  const [selfContributionPct, setSelfContributionPct] = useState<number>(80);
  const [selectedAiTools, setSelectedAiTools] = useState<string[]>([]);
  const [aiUsageDescription, setAiUsageDescription] = useState<string>("");
  const [isPledgeSigned, setIsPledgeSigned] = useState<boolean>(false);

  // Validation Errors
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const fetchAssignment = useCallback(async () => {
    if (!assignmentId) return;
    try {
      setLoading(true);
      const data = await assessmentService.getAssignmentDetail(assignmentId);
      setAssignment(data);
    } catch (err: any) {
      toast.error(resolveErrorMessage(err?.code, "Không thể tải thông tin bài tập."));
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    fetchAssignment();
  }, [fetchAssignment]);

  const handleToolToggle = (toolId: string) => {
    setSelectedAiTools((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId]
    );
  };

  // Due Date & Late Calculation
  const deadlineStatus = useMemo(() => {
    if (!assignment) return null;
    const now = new Date();
    const dueDate = new Date(assignment.due_date);
    const untilDate = assignment.until_date ? new Date(assignment.until_date) : null;

    const isPastDue = now > dueDate;
    const isPastCutoff = untilDate ? now > untilDate : false;

    let diffMs = dueDate.getTime() - now.getTime();
    let text = "";
    if (isPastCutoff) {
      text = "Đã quá hạn chót cho phép nộp bài";
    } else if (isPastDue) {
      const lateDays = Math.ceil((now.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24));
      const penaltyEst = Math.min(100, lateDays * (assignment.late_penalty_percent || 0));
      text = `Trễ hạn ${lateDays} ngày (Trừ ước tính ${penaltyEst}%)`;
    } else {
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      text = `Còn lại ${days} ngày ${hours} giờ`;
    }

    return {
      isPastDue,
      isPastCutoff,
      text,
      dueDate,
      untilDate,
    };
  }, [assignment]);

  // Validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!projectTitle.trim() || projectTitle.trim().length < 5) {
      errors.projectTitle = "Vui lòng nhập tên đề tài / đề án cụ thể của bạn (tối thiểu 5 ký tự).";
    }

    if (submissionTab === "file") {
      if (!selectedFile) {
        errors.file = "Vui lòng chọn tệp bài làm cần nộp.";
      } else if (assignment) {
        const ext = `.${selectedFile.name.split(".").pop()?.toLowerCase()}`;
        const allowed = assignment.allowed_extensions.split(",").map((e) => e.trim().toLowerCase());
        if (!allowed.includes(ext) && !allowed.includes("*")) {
          errors.file = `Định dạng tệp không hợp lệ. Chỉ chấp nhận: ${assignment.allowed_extensions}`;
        }
        if (selectedFile.size > assignment.max_file_size_mb * 1024 * 1024) {
          errors.file = `Dung lượng tệp vượt quá giới hạn ${assignment.max_file_size_mb} MB.`;
        }
      }
    } else {
      if (!gitRepoUrl.trim()) {
        errors.git = "Vui lòng nhập đường dẫn kho mã nguồn Git.";
      } else if (!/^https?:\/\//i.test(gitRepoUrl.trim()) && !/^git@/i.test(gitRepoUrl.trim())) {
        errors.git = "Đường dẫn Git không hợp lệ (Phải bắt đầu bằng https:// hoặc git@).";
      }
    }

    if (aiUsageDescription.trim().length < 20) {
      errors.aiDescription = "Mô tả giải trình sử dụng AI phải đạt tối thiểu 20 ký tự.";
    }

    if (!isPledgeSigned) {
      errors.pledge = "Bạn phải xác nhận cam kết trung thực học thuật trước khi nộp.";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment || !assignmentId) return;

    if (!validateForm()) {
      toast.error("Vui lòng hoàn thiện các trường dữ liệu theo quy định.");
      return;
    }

    if (deadlineStatus?.isPastCutoff) {
      toast.error(resolveErrorMessage("E-SUB-01"));
      return;
    }

    try {
      setSubmitting(true);

      let fileUrl = "";
      let fileName = "";

      if (submissionTab === "file" && selectedFile) {
        fileName = selectedFile.name;
        try {
          const uploadRes = await assessmentService.uploadFile(selectedFile);
          fileUrl = uploadRes.file_url;
          fileName = uploadRes.file_name || selectedFile.name;
        } catch (uploadErr) {
          console.error("Direct upload failed, attempting fallback:", uploadErr);
          const presigned = await assessmentService.getPresignedUploadUrl({
            file_name: selectedFile.name,
            content_type: selectedFile.type || "application/octet-stream",
            file_size_bytes: selectedFile.size,
          });
          fileUrl = presigned.file_url;
        }
      }

      const payload = {
        project_title: projectTitle.trim(),
        file_url: submissionTab === "file" ? fileUrl : undefined,
        file_name: submissionTab === "file" ? fileName : undefined,
        git_repo_url: submissionTab === "git" ? gitRepoUrl.trim() : undefined,
        comments: studentComments.trim() || undefined,
        ai_disclosure: {
          self_contribution_pct: selfContributionPct,
          tools_used: selectedAiTools,
          usage_description: aiUsageDescription.trim(),
        },
        is_pledge_signed: isPledgeSigned,
      };

      const result = await assessmentService.createSubmission(assignmentId, payload);
      toast.success(`Nộp bài thành công (Phiên bản v${result.version})!`);

      // Reset form fields
      setSelectedFile(null);
      setGitRepoUrl("");
      setStudentComments("");
      setIsPledgeSigned(false);
      setFormErrors({});

      // Refresh list
      await fetchAssignment();
    } catch (err: any) {
      toast.error(resolveErrorMessage(err?.code, err?.message || "Không thể gửi bài nộp."));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-mm-blue-primary border-t-transparent" />
          <span className="font-mm-ui text-sm text-[#6b7280]">Đang tải thông tin bài tập...</span>
        </div>
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="mx-auto max-w-4xl p-8 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-[#991b1b]" />
        <h2 className="mt-4 font-mm-display text-xl font-semibold text-mm-heading">Không tìm thấy bài tập</h2>
        <p className="mt-2 font-mm-ui text-sm text-[#6b7280]">Bài tập này có thể chưa được kích hoạt hoặc bạn không có quyền truy cập.</p>
        <MmButton className="mt-6" variant="secondary" onClick={() => navigate(-1)}>
          Quay lại
        </MmButton>
      </div>
    );
  }

  const latestSubmission: Submission | undefined =
    assignment.submissions && assignment.submissions.length > 0
      ? assignment.submissions[0]
      : undefined;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Top Breadcrumb & Title */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[#e5e7eb] pb-5">
        <div className="flex items-center gap-3">
          <Link
            to={courseId ? `/courses/${courseId}` : "/courses"}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[#e5e7eb] bg-white text-[#4b5563] transition-colors hover:bg-gray-50 hover:text-mm-dark"
            title="Quay lại danh sách bài tập môn học"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-[#6b7280]">
              <span>Môn học</span>
              <span>/</span>
              <span className="text-mm-blue-primary">Đánh giá năng lực</span>
            </div>
            <h1 className="mt-1 font-mm-display text-2xl font-bold text-mm-dark tracking-tight sm:text-3xl">
              {assignment.title}
            </h1>
          </div>
        </div>

        {/* Minimalist Academic Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {assignment.is_viva_required && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#dbeafe] bg-[#eff6ff] px-3 py-1 text-xs font-medium text-[#1e40af]">
              <Sparkles className="h-3.5 w-3.5 text-mm-blue-primary" />
              <span>Vấn đáp Viva ({assignment.viva_question_count || 5} câu)</span>
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#e5e7eb] bg-[#f9fafb] px-3 py-1 text-xs font-medium text-[#374151]">
            <Bot className="h-3.5 w-3.5 text-[#4b5563]" />
            <span>Khai báo sử dụng AI</span>
          </span>
        </div>
      </div>

      {/* Main Grid: Left 8 cols (Instructions & Submission Form), Right 4 cols (Schedule & Viva & History) */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Column */}
        <div className="lg:col-span-8 space-y-8">
          {/* Instructions Card with Rendered Markdown */}
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 sm:p-7 shadow-xs">
            <div className="mb-4 border-b border-[#f3f4f6] pb-3">
              <h2 className="font-mm-display text-lg font-bold text-mm-dark">
                Nội dung đề bài & Hướng dẫn thực hiện
              </h2>
              <p className="text-xs text-[#6b7280]">
                Quy cách thực hiện bài làm do giảng viên công bố
              </p>
            </div>

            <div className="prose prose-sm max-w-none text-[#374151] leading-relaxed">
              <MarkdownRenderer content={assignment.instructions} />
            </div>

            {assignment.attachment_url && (
              <div className="mt-6 flex items-center justify-between rounded-xl border border-[#e5e7eb] bg-[#f9fafb] px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-medium text-mm-dark">
                  <FileText className="h-4 w-4 text-mm-blue-primary" />
                  <span>Tài liệu đính kèm đề bài</span>
                </div>
                <a
                  href={assignment.attachment_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-mm-blue-primary hover:underline"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Tải tệp</span>
                </a>
              </div>
            )}
          </div>

          {/* Submission Form Card */}
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 sm:p-8 shadow-xs">
            <div className="mb-6 flex items-center justify-between border-b border-[#f3f4f6] pb-4">
              <div>
                <h2 className="font-mm-display text-xl font-bold text-mm-dark">
                  Khu vực nộp bài tập
                </h2>
                <p className="mt-0.5 text-xs text-[#6b7280]">
                  Gửi sản phẩm thực hiện, khai báo tên đề tài và bảng giải trình sử dụng AI
                </p>
              </div>
              <span className="rounded-full border border-[#e5e7eb] bg-[#f9fafb] px-3 py-1 font-mm-mono text-xs font-medium text-[#374151]">
                Lần nộp: v{(assignment.submissions?.length || 0) + 1}
              </span>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Field 1: Specific Student Project / Topic Title */}
              <div>
                <label className="block text-xs font-semibold text-mm-dark uppercase tracking-wider mb-1.5">
                  Tên đề tài / Đồ án cụ thể của bạn <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={projectTitle}
                  onChange={(e) => {
                    setProjectTitle(e.target.value);
                    if (e.target.value.trim().length >= 5) {
                      setFormErrors((prev) => ({ ...prev, projectTitle: "" }));
                    }
                  }}
                  placeholder="Ví dụ: Nghiên cứu mô hình Active Learning cho bài toán trích xuất thực thể tiếng Việt..."
                  className={clsx(
                    "w-full rounded-xl border bg-white px-4 py-2.5 text-sm font-mm-ui text-mm-dark transition-colors focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20",
                    formErrors.projectTitle ? "border-rose-400" : "border-[#e5e7eb]"
                  )}
                />
                {formErrors.projectTitle ? (
                  <p className="mt-1 text-xs text-rose-600">{formErrors.projectTitle}</p>
                ) : (
                  <p className="mt-1 text-[11px] text-[#6b7280]">
                    AI sẽ dùng trực tiếp tên đề tài cụ thể này cùng mã nguồn/báo cáo của bạn để đặt câu hỏi vấn đáp Viva phù hợp.
                  </p>
                )}
              </div>

              {/* Submission Mode Selector */}
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
                  Phương thức gửi bài
                </label>
                <PillTabs
                  items={[
                    { value: "file", label: "Tải lên tệp dự án" },
                    { value: "git", label: "Kho lưu trữ Git" },
                  ]}
                  value={submissionTab}
                  onChange={setSubmissionTab}
                />
              </div>

              {/* File Upload Zone */}
              {submissionTab === "file" && (
                <div>
                  <div
                    className={clsx(
                      "relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all",
                      formErrors.file
                        ? "border-rose-400 bg-rose-50/20"
                        : "border-[#e5e7eb] hover:border-mm-blue-primary/60 bg-[#fafafa]"
                    )}
                  >
                    <input
                      type="file"
                      id="assignment-file-input"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setSelectedFile(e.target.files[0]);
                          setFormErrors((prev) => ({ ...prev, file: "" }));
                        }
                      }}
                    />
                    <div className="rounded-xl bg-white p-3 shadow-xs border border-[#e5e7eb] text-mm-blue-primary">
                      <UploadCloud className="h-6 w-6" />
                    </div>
                    {selectedFile ? (
                      <div className="mt-3">
                        <p className="font-mm-ui text-sm font-semibold text-mm-dark">{selectedFile.name}</p>
                        <p className="text-xs text-[#6b7280]">
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                        <button
                          type="button"
                          onClick={() => setSelectedFile(null)}
                          className="mt-2 inline-flex items-center gap-1 text-xs text-rose-600 hover:underline"
                        >
                          Xóa tệp đã chọn
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3">
                        <label
                          htmlFor="assignment-file-input"
                          className="cursor-pointer font-mm-ui text-sm font-medium text-mm-blue-primary hover:underline"
                        >
                          Nhấp để duyệt tệp
                        </label>
                        <span className="text-xs text-[#6b7280]"> hoặc kéo thả vào đây</span>
                        <p className="mt-1 text-xs text-[#9ca3af]">
                          Định dạng: {assignment.allowed_extensions} (Tối đa {assignment.max_file_size_mb} MB)
                        </p>
                      </div>
                    )}
                  </div>
                  {formErrors.file && (
                    <p className="mt-1.5 text-xs text-rose-600">{formErrors.file}</p>
                  )}
                </div>
              )}

              {/* Git Repository Zone */}
              {submissionTab === "git" && (
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
                    Địa chỉ Git Repository (GitHub, GitLab)
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-[#9ca3af]">
                      <GitBranch className="h-4 w-4" />
                    </div>
                    <input
                      type="url"
                      value={gitRepoUrl}
                      onChange={(e) => {
                        setGitRepoUrl(e.target.value);
                        setFormErrors((prev) => ({ ...prev, git: "" }));
                      }}
                      placeholder="https://github.com/organization/repo-name.git"
                      className={clsx(
                        "w-full rounded-xl border bg-white py-2.5 pl-10 pr-4 text-sm font-mm-ui text-mm-dark transition-colors focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20",
                        formErrors.git ? "border-rose-400" : "border-[#e5e7eb]"
                      )}
                    />
                  </div>
                  {formErrors.git && (
                    <p className="text-xs text-rose-600">{formErrors.git}</p>
                  )}
                </div>
              )}

              {/* Student Comments */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
                  Ghi chú đính kèm (Tùy chọn)
                </label>
                <textarea
                  rows={2}
                  value={studentComments}
                  onChange={(e) => setStudentComments(e.target.value)}
                  placeholder="Ghi chú thêm về phiên bản hoặc các điểm lưu ý cho giảng viên..."
                  className="w-full rounded-xl border border-[#e5e7eb] bg-white p-3 text-sm font-mm-ui text-mm-dark transition-colors focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20"
                />
              </div>

              {/* AI Disclosure Section - Clean & Sober Design */}
              <div className="rounded-2xl border border-[#e5e7eb] bg-[#fcfdfe] p-5 sm:p-6 space-y-5">
                <div className="flex items-center gap-2.5 border-b border-[#f3f4f6] pb-3">
                  <div className="rounded-lg bg-gray-100 p-2 text-mm-dark">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="font-mm-display text-sm font-bold text-mm-dark">
                      Bảng Tự Khai Báo Sử Dụng AI (AI Disclosure)
                    </h3>
                    <p className="text-[11px] text-[#6b7280]">
                      Minh bạch công cụ AI hỗ trợ theo quy chuẩn khảo thí OLP 2026
                    </p>
                  </div>
                </div>

                {/* Contribution Slider */}
                <div>
                  <div className="mb-2 flex items-center justify-between text-xs">
                    <span className="font-medium text-mm-dark">
                      Mức độ tự thực hiện của bạn:
                    </span>
                    <span className="font-mm-mono font-semibold text-mm-blue-deep bg-[#eff6ff] border border-[#bfdbfe] px-2.5 py-0.5 rounded-full">
                      {selfContributionPct}% Tự làm ({100 - selfContributionPct}% AI hỗ trợ)
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={selfContributionPct}
                    onChange={(e) => setSelfContributionPct(Number(e.target.value))}
                    className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 accent-mm-blue-primary"
                  />
                  <div className="mt-1 flex justify-between text-[11px] text-[#9ca3af]">
                    <span>0% (Hoàn toàn AI)</span>
                    <span>50% (Đồng sáng tạo)</span>
                    <span>100% (Tự viết hoàn toàn)</span>
                  </div>
                </div>

                {/* AI Tools Checkboxes */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-mm-dark">
                    Các công cụ AI bạn đã sử dụng:
                  </label>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {AI_TOOL_OPTIONS.map((tool) => {
                      const checked = selectedAiTools.includes(tool.id);
                      return (
                        <button
                          type="button"
                          key={tool.id}
                          onClick={() => handleToolToggle(tool.id)}
                          className={clsx(
                            "flex items-center gap-2 rounded-xl border p-2.5 text-left text-xs transition-colors",
                            checked
                              ? "border-mm-blue-primary bg-[#eff6ff] text-mm-blue-deep font-medium"
                              : "border-[#e5e7eb] bg-white text-[#4b5563] hover:bg-gray-50"
                          )}
                        >
                          <div
                            className={clsx(
                              "flex h-4 w-4 items-center justify-center rounded border",
                              checked
                                ? "border-mm-blue-primary bg-mm-blue-primary text-white"
                                : "border-gray-300 bg-white"
                            )}
                          >
                            {checked && <CheckCircle2 className="h-3 w-3 stroke-[3]" />}
                          </div>
                          <span>{tool.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* AI Usage Description */}
                <div>
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <label className="font-medium text-mm-dark">
                      Giải trình phương thức dùng AI & Prompt chính (Tối thiểu 20 ký tự):
                    </label>
                    <span
                      className={clsx(
                        "font-mm-mono text-[11px]",
                        aiUsageDescription.trim().length >= 20 ? "text-[#15803d]" : "text-rose-600 font-medium"
                      )}
                    >
                      {aiUsageDescription.trim().length} / 20 ký tự
                    </span>
                  </div>
                  <textarea
                    rows={3}
                    value={aiUsageDescription}
                    onChange={(e) => {
                      setAiUsageDescription(e.target.value);
                      if (e.target.value.trim().length >= 20) {
                        setFormErrors((prev) => ({ ...prev, aiDescription: "" }));
                      }
                    }}
                    placeholder="Mô tả cụ thể bạn dùng AI ở phần nào, prompt chính bạn đã nhập, và cách bạn kiểm chứng kết quả..."
                    className={clsx(
                      "w-full rounded-xl border bg-white p-3 text-xs font-mm-ui text-mm-dark transition-colors focus:outline-none focus:ring-2 focus:ring-mm-blue-primary/20",
                      formErrors.aiDescription ? "border-rose-400" : "border-[#e5e7eb]"
                    )}
                  />
                  {formErrors.aiDescription && (
                    <p className="mt-1 text-xs text-rose-600">{formErrors.aiDescription}</p>
                  )}
                </div>
              </div>

              {/* Integrity Pledge Checkbox */}
              <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isPledgeSigned}
                    onChange={(e) => {
                      setIsPledgeSigned(e.target.checked);
                      if (e.target.checked) setFormErrors((prev) => ({ ...prev, pledge: "" }));
                    }}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-mm-blue-primary focus:ring-mm-blue-primary"
                  />
                  <div className="text-xs text-[#374151] leading-relaxed font-mm-ui">
                    <span className="font-semibold text-mm-dark">Cam kết liêm chính học thuật:</span> Tôi xin cam đoan đây là công trình học tập do chính tôi thực hiện theo đúng các khai báo ở trên. Tôi hoàn toàn chịu trách nhiệm trước hội đồng khảo thí.
                  </div>
                </label>
                {formErrors.pledge && (
                  <p className="mt-1.5 text-xs text-rose-600">{formErrors.pledge}</p>
                )}
              </div>

              {/* Submit CTA */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <MmButton
                  type="submit"
                  variant="brand"
                  size="md"
                  loading={submitting}
                  disabled={submitting || deadlineStatus?.isPastCutoff}
                  className="rounded-full shadow-sm"
                >
                  <FileCheck2 className="h-4 w-4 mr-2" />
                  Nộp bài tập (Phiên bản v{(assignment.submissions?.length || 0) + 1})
                </MmButton>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Schedule & Viva CTA & History */}
        <div className="lg:col-span-4 space-y-6">
          {/* Viva Defense Room Card (Sober, Academic, Non-Plastic) */}
          {assignment.is_viva_required && (
            <div className="rounded-2xl border border-[#dbeafe] bg-white p-6 shadow-xs">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mm-blue-primary">
                <ShieldCheck className="h-4 w-4" />
                <span>Phòng Vấn Đáp Cô Lập</span>
              </div>
              <h3 className="mt-2 font-mm-display text-lg font-bold text-mm-dark">
                Bảo Vệ Đồ Án Viva Sandbox
              </h3>
              <p className="mt-1 text-xs text-[#6b7280] leading-relaxed">
                Hệ thống AI sẽ đặt {assignment.viva_question_count || 5} câu hỏi phản biện trực tiếp dựa trên đề tài và bài nộp cụ thể của bạn để xác thực năng lực thực chất.
              </p>

              {latestSubmission ? (
                <div className="mt-5 space-y-3 border-t border-[#f3f4f6] pt-4">
                  <div className="text-xs">
                    <span className="text-[#6b7280]">Đề tài đã nộp:</span>
                    <p className="font-semibold text-mm-dark line-clamp-2 mt-0.5">
                      {latestSubmission.project_title || assignment.title}
                    </p>
                    <p className="text-[11px] text-[#9ca3af] font-mm-mono mt-0.5">
                      Phiên bản v{latestSubmission.version} • {new Date(latestSubmission.submitted_at).toLocaleTimeString("vi-VN")}
                    </p>
                  </div>

                  <MmButton
                    variant="brand"
                    size="md"
                    fullWidth
                    onClick={() => navigate(`/viva/${latestSubmission.id}`)}
                    className="rounded-full shadow-sm"
                  >
                    <span>Vào Phòng Vấn Đáp Viva</span>
                    <ArrowRight className="h-4 w-4 ml-1.5" />
                  </MmButton>
                </div>
              ) : (
                <div className="mt-4 rounded-xl bg-gray-50 p-3 text-center text-xs text-[#6b7280]">
                  Vui lòng nộp bài tập trước khi kích hoạt phòng thi Viva Sandbox.
                </div>
              )}
            </div>
          )}

          {/* Schedule & Late Penalty Summary */}
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs space-y-4">
            <h3 className="font-mm-display text-sm font-bold text-mm-dark border-b border-[#f3f4f6] pb-3">
              Quy chế nộp bài & Hạn chót
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[#6b7280]">Hạn chót nộp (Due Date):</span>
                <p className="font-mm-mono font-semibold text-mm-dark mt-0.5">
                  {new Date(assignment.due_date).toLocaleString("vi-VN", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>
                <p className={clsx("mt-0.5 font-medium", deadlineStatus?.isPastDue ? "text-amber-600" : "text-[#15803d]")}>
                  {deadlineStatus?.text}
                </p>
              </div>

              {assignment.until_date && (
                <div className="border-t border-[#f3f4f6] pt-3">
                  <span className="text-[#6b7280]">Hạn cắt nộp trễ (Until Date):</span>
                  <p className="font-mm-mono font-semibold text-mm-dark mt-0.5">
                    {new Date(assignment.until_date).toLocaleString("vi-VN", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                </div>
              )}

              <div className="border-t border-[#f3f4f6] pt-3">
                <span className="text-[#6b7280]">Quy định nộp trễ (BR-11):</span>
                <p className="font-medium text-mm-dark mt-0.5">
                  Trừ {assignment.late_penalty_percent}% / mỗi ngày nộp muộn
                </p>
              </div>
            </div>
          </div>

          {/* Submission History Card */}
          <div className="rounded-2xl border border-[#e5e7eb] bg-white p-6 shadow-xs">
            <div className="mb-4 flex items-center justify-between border-b border-[#f3f4f6] pb-3">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-mm-blue-primary" />
                <h3 className="font-mm-display text-sm font-bold text-mm-dark">
                  Lịch sử nộp bài ({assignment.submissions?.length || 0})
                </h3>
              </div>
            </div>

            {assignment.submissions && assignment.submissions.length > 0 ? (
              <div className="space-y-3">
                {assignment.submissions.map((sub) => (
                  <div
                    key={sub.id}
                    className="rounded-xl border border-[#e5e7eb] p-3.5 transition-colors hover:border-gray-300"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mm-display text-xs font-bold text-mm-dark">
                        Phiên bản v{sub.version}
                      </span>
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 font-mm-mono text-[10px] font-semibold",
                          sub.is_late
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-[#ecfdf5] text-[#047857] border border-[#a7f3d0]"
                        )}
                      >
                        {sub.is_late ? `Trễ (-${sub.late_penalty_applied}%)` : "Đúng hạn"}
                      </span>
                    </div>

                    {sub.project_title && (
                      <p className="mt-1.5 text-xs font-medium text-mm-dark line-clamp-1">
                        {sub.project_title}
                      </p>
                    )}

                    <div className="mt-1 text-[11px] text-[#9ca3af] font-mm-mono">
                      {new Date(sub.submitted_at).toLocaleString("vi-VN")}
                    </div>

                    <div className="mt-2 text-xs truncate">
                      {sub.git_repo_url ? (
                        <div className="flex items-center gap-1.5 text-mm-blue-primary text-[11px]">
                          <GitBranch className="h-3 w-3 flex-shrink-0" />
                          <span className="truncate">{sub.git_repo_url}</span>
                        </div>
                      ) : sub.file_url ? (
                        <div className="flex items-center gap-1.5 text-[#6b7280] text-[11px]">
                          <FileText className="h-3 w-3 flex-shrink-0" />
                          <span className="truncate">Tệp bài nộp đính kèm</span>
                        </div>
                      ) : null}
                    </div>

                    <div className="mt-2.5 flex items-center justify-between border-t border-[#f3f4f6] pt-2 text-[10px] text-[#6b7280]">
                      <span>Tự làm: {sub.self_contribution_pct}%</span>
                      <span className="font-medium text-mm-dark">{sub.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-[#9ca3af]">
                Chưa có lượt nộp bài nào.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
