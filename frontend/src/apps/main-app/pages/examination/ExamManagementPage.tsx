/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Award,
  BookMarked,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Edit3,
  FileCheck2,
  FolderPlus,
  KeyRound,
  Play,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import type { BloomLevel, CourseDetail } from "../../../../types/course";
import type {
  QuestionBankResponse,
  QuestionResponse,
  QuizSummaryResponse,
  RegradeStatus,
  RegradeSummaryResponse,
} from "../../../../types/examination";
import { BloomBadge } from "../../components/BloomBadge";
import { ConfirmModal } from "../../components/ConfirmModal";
import { mmInputClass } from "../../components/FormField";
import { MathCodeContent } from "../../components/MathCodeContent";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { PillTabs, type PillTabItem } from "../../components/PillTabs";
import { showToast } from "../../components/Toast";
import { StudentLayout } from "../../layouts/StudentLayout";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { CreateQuizMatrixModal } from "./CreateQuizMatrixModal";
import {
  BLOOM_OPTIONS,
  formatDateTime,
  formatScore,
  getLastSubmissionStorageKey,
  GRADE_RELEASE_LABELS,
  QUESTION_TYPE_LABELS,
  QUIZ_STATUS_META,
  REGRADE_SCOPE_LABELS,
  REGRADE_STATUS_META,
  SECURITY_MODE_LABELS,
  toNumeric,
} from "./examHelpers";
import { QuestionFormModal } from "./QuestionFormModal";
import { QuizSecuritySettingsModal } from "./QuizSecuritySettingsModal";
import { RegradeReviewModal } from "./RegradeReviewModal";

type ManagementTab = "bank" | "quizzes" | "regrades";

export const ExamManagementPage: React.FC = () => {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const me = useAuthStore((s) => s.me);

  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ManagementTab>("quizzes");

  // Bank & Questions state
  const [banks, setBanks] = useState<QuestionBankResponse[]>([]);
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [newBankName, setNewBankName] = useState("");
  const [creatingBank, setCreatingBank] = useState(false);
  const [filterBankId, setFilterBankId] = useState("");
  const [filterLoId, setFilterLoId] = useState("");
  const [filterBloom, setFilterBloom] = useState<BloomLevel | "">("");
  const [searchQuery, setSearchQuery] = useState("");

  // Question modals
  const [questionModalOpen, setQuestionModalOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<QuestionResponse | null>(null);
  const [deletingQuestion, setDeletingQuestion] = useState<QuestionResponse | null>(null);
  const [deletingQuestionLoading, setDeletingQuestionLoading] = useState(false);
  const [deletingBank, setDeletingBank] = useState<QuestionBankResponse | null>(null);
  const [deletingBankLoading, setDeletingBankLoading] = useState(false);

  // Quizzes state
  const [quizzes, setQuizzes] = useState<QuizSummaryResponse[]>([]);
  const [createQuizOpen, setCreateQuizOpen] = useState(false);
  const [settingsQuiz, setSettingsQuiz] = useState<QuizSummaryResponse | null>(null);
  const [publishingQuizId, setPublishingQuizId] = useState<string | null>(null);
  const [publishingGradesId, setPublishingGradesId] = useState<string | null>(null);

  // Regrades state
  const [selectedRegradeQuizId, setSelectedRegradeQuizId] = useState("");
  const [regradeStatusFilter, setRegradeStatusFilter] = useState<RegradeStatus | "">("");
  const [regrades, setRegrades] = useState<RegradeSummaryResponse[]>([]);
  const [loadingRegrades, setLoadingRegrades] = useState(false);
  const [reviewingRegrade, setReviewingRegrade] =
    useState<RegradeSummaryResponse | null>(null);

  const isInstructor =
    course?.my_role === "INSTRUCTOR" ||
    course?.my_role === "TA" ||
    me?.system_role === "ADMIN";

  const loadInstructorData = useCallback(async () => {
    if (!courseId) return;
    const [bankList, questionList, quizList] = await Promise.all([
      examinationService.listQuestionBanks(courseId),
      examinationService.listQuestions(courseId),
      examinationService.listQuizzes(courseId),
    ]);
    setBanks(bankList);
    setQuestions(questionList);
    setQuizzes(quizList);
    if (quizList.length > 0) {
      setSelectedRegradeQuizId((prev) => prev || quizList[0].id);
    }
  }, [courseId]);

  const loadAll = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    try {
      const detail = await courseService.getCourseDetail(courseId);
      setCourse(detail);
      const instructorRole =
        detail.my_role === "INSTRUCTOR" ||
        detail.my_role === "TA" ||
        me?.system_role === "ADMIN";

      if (instructorRole) {
        await loadInstructorData();
      } else {
        const quizList = await examinationService.listQuizzes(courseId);
        setQuizzes(quizList);
      }
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError
          ? err.message
          : "Không thể tải dữ liệu Ngân hàng đề và Khảo thí."
      );
    } finally {
      setLoading(false);
    }
  }, [courseId, me?.system_role, loadInstructorData]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const loadRegrades = useCallback(async () => {
    if (!isInstructor || !selectedRegradeQuizId) {
      setRegrades([]);
      return;
    }
    setLoadingRegrades(true);
    try {
      const list = await examinationService.listQuizRegrades(
        selectedRegradeQuizId,
        regradeStatusFilter || undefined
      );
      setRegrades(list);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError
          ? err.message
          : "Không thể tải danh sách đơn phúc khảo."
      );
    } finally {
      setLoadingRegrades(false);
    }
  }, [isInstructor, selectedRegradeQuizId, regradeStatusFilter]);

  useEffect(() => {
    if (activeTab === "regrades") {
      void loadRegrades();
    }
  }, [activeTab, loadRegrades]);

  const filteredQuestions = useMemo(() => {
    const qLower = searchQuery.trim().toLowerCase();
    return questions.filter((item) => {
      if (filterBankId && item.bank_id !== filterBankId) return false;
      if (filterLoId && item.lo_id !== filterLoId) return false;
      if (filterBloom && item.bloom_level !== filterBloom) return false;
      if (qLower && !item.question_text.toLowerCase().includes(qLower)) return false;
      return true;
    });
  }, [questions, filterBankId, filterLoId, filterBloom, searchQuery]);

  const bankNameMap = useMemo(() => {
    const map = new Map<string, string>();
    banks.forEach((b) => map.set(b.id, b.category_name));
    return map;
  }, [banks]);

  const loCodeMap = useMemo(() => {
    const map = new Map<string, string>();
    course?.learning_objectives.forEach((lo) => map.set(lo.id, lo.code));
    return map;
  }, [course?.learning_objectives]);

  const handleCreateBank = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleaned = newBankName.trim();
    if (cleaned.length < 2) {
      showToast("error", "Tên danh mục ngân hàng phải có ít nhất 2 ký tự.");
      return;
    }
    setCreatingBank(true);
    try {
      await examinationService.createQuestionBank(courseId, {
        category_name: cleaned,
      });
      setNewBankName("");
      showToast("success", `Đã tạo danh mục "${cleaned}".`);
      await loadInstructorData();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tạo danh mục ngân hàng."
      );
    } finally {
      setCreatingBank(false);
    }
  };

  const handleDeleteBank = async () => {
    if (!deletingBank) return;
    setDeletingBankLoading(true);
    try {
      await examinationService.deleteQuestionBank(deletingBank.id);
      showToast("success", `Đã xóa danh mục "${deletingBank.category_name}".`);
      if (filterBankId === deletingBank.id) setFilterBankId("");
      setDeletingBank(null);
      await loadInstructorData();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xóa danh mục ngân hàng."
      );
    } finally {
      setDeletingBankLoading(false);
    }
  };

  const handleDeleteQuestion = async () => {
    if (!deletingQuestion) return;
    setDeletingQuestionLoading(true);
    try {
      const res = await examinationService.deleteQuestion(deletingQuestion.id);
      showToast("success", res.message);
      setDeletingQuestion(null);
      await loadInstructorData();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xóa câu hỏi."
      );
    } finally {
      setDeletingQuestionLoading(false);
    }
  };

  const handlePublishQuiz = async (quiz: QuizSummaryResponse) => {
    setPublishingQuizId(quiz.id);
    try {
      await examinationService.publishQuiz(quiz.id);
      showToast(
        "success",
        `Đã xuất bản kỳ thi "${quiz.title}" và đóng băng đề Snapshot.`
      );
      await loadInstructorData();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xuất bản kỳ thi."
      );
    } finally {
      setPublishingQuizId(null);
    }
  };

  const handlePublishGrades = async (quiz: QuizSummaryResponse) => {
    setPublishingGradesId(quiz.id);
    try {
      await examinationService.publishGrades(quiz.id);
      showToast(
        "success",
        `Đã công bố điểm cho "${quiz.title}". Cửa sổ phúc khảo 48 giờ bắt đầu tính từ lúc này.`
      );
      await loadInstructorData();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể công bố điểm."
      );
    } finally {
      setPublishingGradesId(null);
    }
  };

  const Layout = isInstructor ? TeacherLayout : StudentLayout;

  const tabs: PillTabItem<ManagementTab>[] = [
    {
      value: "bank",
      label: "Ngân hàng câu hỏi",
      count: questions.length,
      icon: <BookMarked className="h-4 w-4" />,
    },
    {
      value: "quizzes",
      label: "Kỳ thi & Phòng thi",
      count: quizzes.length,
      icon: <ClipboardCheck className="h-4 w-4" />,
    },
    {
      value: "regrades",
      label: "Đơn phúc khảo",
      count: regrades.filter((r) => r.status === "PENDING").length || undefined,
      icon: <FileCheck2 className="h-4 w-4" />,
    },
  ];

  return (
    <Layout>
      {loading ? (
        <div className="space-y-4">
          <div className="h-10 w-72 animate-pulse rounded-mm-btn bg-mm-divider" />
          <div className="h-64 animate-pulse rounded-mm-card bg-mm-divider/60" />
        </div>
      ) : !course ? (
        <MmCard variant="standard" className="py-12 text-center">
          <p className="font-mm-ui text-base text-mm-text-secondary">
            Không tìm thấy môn học hoặc bạn không có quyền truy cập.
          </p>
          <Link to="/courses" className="mt-4 inline-block">
            <MmButton variant="secondary">
              <ArrowLeft className="h-4 w-4" />
              <span>Quay lại danh sách môn học</span>
            </MmButton>
          </Link>
        </MmCard>
      ) : (
        <div className="space-y-6">
          <div>
            <Link
              to={`/courses/${course.id}`}
              className="mb-3 inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Quay lại môn học: {course.name}</span>
            </Link>

            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <p className="font-mm-data text-xs text-mm-text-muted">
                  {course.course_code} · {course.section_code} · {course.semester}
                </p>
                <h1 className="mt-1 font-mm-display text-[30px] font-semibold tracking-tight text-mm-heading">
                  Ngân hàng đề & Khảo thí
                </h1>
              </div>

              {isInstructor && (
                <div className="flex flex-wrap items-center gap-2.5">
                  <MmButton
                    variant="secondary"
                    onClick={() => {
                      setEditingQuestion(null);
                      setQuestionModalOpen(true);
                    }}
                    disabled={banks.length === 0}
                  >
                    <Plus className="h-4 w-4" />
                    <span>Soạn câu hỏi</span>
                  </MmButton>
                  <MmButton
                    variant="brand"
                    onClick={() => setCreateQuizOpen(true)}
                    disabled={banks.length === 0}
                  >
                    <ClipboardCheck className="h-4 w-4" />
                    <span>Tạo đề theo ma trận</span>
                  </MmButton>
                </div>
              )}
            </div>
          </div>

          {isInstructor ? (
            <>
              <PillTabs items={tabs} value={activeTab} onChange={setActiveTab} />

              {activeTab === "bank" && (
                <div className="space-y-5">
                  <MmCard variant="standard" radius="card" padding="md">
                    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                      <div>
                        <h2 className="font-mm-mid text-lg font-medium text-mm-heading">
                          Chương / Danh mục ngân hàng câu hỏi
                        </h2>
                        <p className="font-mm-ui text-xs text-mm-text-secondary">
                          Tổ chức câu hỏi theo chương để bốc đề ngẫu nhiên theo ma trận Snapshot
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link to={`/courses/${courseId}/question-bank`}>
                          <MmButton variant="primary" size="sm">
                            <Sparkles className="h-4 w-4" />
                            <span>Thư mục đa cấp & Trích xuất AI</span>
                          </MmButton>
                        </Link>
                        <form
                          onSubmit={handleCreateBank}
                          className="flex w-full max-w-md items-center gap-2"
                        >
                        <input
                          type="text"
                          value={newBankName}
                          onChange={(e) => setNewBankName(e.target.value)}
                          placeholder="Tên chương mới (vd: Chương 1 - Độ phức tạp)"
                          className={mmInputClass(false)}
                        />
                        <MmButton
                          type="submit"
                          variant="brand"
                          size="sm"
                          loading={creatingBank}
                          className="shrink-0"
                        >
                          <FolderPlus className="h-4 w-4" />
                          <span>Tạo chương</span>
                        </MmButton>
                      </form>
                    </div>
                  </div>

                    {banks.length === 0 ? (
                      <p className="mt-4 font-mm-ui text-sm text-mm-text-muted">
                        Chưa có danh mục nào. Hãy tạo ít nhất 1 chương trước khi soạn câu hỏi.
                      </p>
                    ) : (
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setFilterBankId("")}
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-mm-ui text-xs font-medium transition-colors ${
                            filterBankId === ""
                              ? "border-mm-dark bg-mm-dark text-white"
                              : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/50"
                          }`}
                        >
                          <span>Tất cả chương</span>
                          <span className="font-mm-data opacity-80">
                            ({questions.length})
                          </span>
                        </button>
                        {banks.map((bank) => (
                          <div
                            key={bank.id}
                            className={`inline-flex items-center gap-1 rounded-full border pl-3.5 pr-1.5 py-1 font-mm-ui text-xs font-medium transition-colors ${
                              filterBankId === bank.id
                                ? "border-mm-blue-hover bg-mm-blue-light/25 text-mm-blue-hover"
                                : "border-mm-border bg-mm-bg text-mm-heading hover:bg-mm-divider/40"
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => setFilterBankId(bank.id)}
                              className="inline-flex items-center gap-1.5"
                            >
                              <span>{bank.category_name}</span>
                              <span className="font-mm-data text-[11px] opacity-75">
                                ({bank.question_count})
                              </span>
                            </button>
                            <button
                              type="button"
                              title="Xóa danh mục"
                              onClick={() => setDeletingBank(bank)}
                              className="ml-1 rounded-full p-1 text-mm-text-muted hover:bg-mm-danger-bg hover:text-mm-danger"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </MmCard>

                  <MmCard variant="standard" radius="card" padding="none">
                    <div className="flex flex-col gap-3 border-b border-mm-divider px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
                        <div className="relative">
                          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mm-text-muted" />
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Tìm nội dung câu hỏi..."
                            className={`${mmInputClass(false)} pl-9`}
                          />
                        </div>

                        <select
                          aria-label="Lọc theo Chuẩn đầu ra"
                          value={filterLoId}
                          onChange={(e) => setFilterLoId(e.target.value)}
                          className={mmInputClass(false)}
                        >
                          <option value="">Tất cả Chuẩn đầu ra (LO)</option>
                          {course.learning_objectives.map((lo) => (
                            <option key={lo.id} value={lo.id}>
                              {lo.code} - {lo.description}
                            </option>
                          ))}
                        </select>

                        <select
                          aria-label="Lọc theo mức Bloom"
                          value={filterBloom}
                          onChange={(e) =>
                            setFilterBloom(e.target.value as BloomLevel | "")
                          }
                          className={mmInputClass(false)}
                        >
                          <option value="">Tất cả mức nhận thức Bloom</option>
                          {BLOOM_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <MmButton
                        variant="brand"
                        size="sm"
                        disabled={banks.length === 0}
                        onClick={() => {
                          setEditingQuestion(null);
                          setQuestionModalOpen(true);
                        }}
                      >
                        <Plus className="h-4 w-4" />
                        <span>Thêm câu hỏi</span>
                      </MmButton>
                    </div>

                    {filteredQuestions.length === 0 ? (
                      <div className="p-12 text-center">
                        <BookMarked className="mx-auto mb-3 h-9 w-9 text-mm-text-muted" />
                        <p className="font-mm-ui text-sm text-mm-text-secondary">
                          Chưa có câu hỏi nào khớp với bộ lọc hiện tại.
                        </p>
                      </div>
                    ) : (
                      <div className="divide-y divide-mm-divider">
                        {filteredQuestions.map((q, idx) => (
                          <div
                            key={q.id}
                            className="flex flex-col justify-between gap-4 px-6 py-4 hover:bg-mm-divider/15 sm:flex-row sm:items-start"
                          >
                            <div className="min-w-0 flex-1 space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-mm-mono text-xs text-mm-text-muted">
                                  #{idx + 1}
                                </span>
                                <span className="rounded-mm-tag bg-mm-divider px-2 py-0.5 font-mm-ui text-xs text-mm-text-secondary">
                                  {bankNameMap.get(q.bank_id) ?? "Danh mục"}
                                </span>
                                {q.lo_id && loCodeMap.get(q.lo_id) && (
                                  <span className="rounded-mm-tag bg-mm-blue-light/30 px-2 py-0.5 font-mm-mono text-xs font-medium text-mm-blue-hover">
                                    {loCodeMap.get(q.lo_id)}
                                  </span>
                                )}
                                <BloomBadge level={q.bloom_level} />
                                <span className="rounded-mm-tag border border-mm-border px-2 py-0.5 font-mm-ui text-xs text-mm-text-secondary">
                                  {QUESTION_TYPE_LABELS[q.question_type]}
                                </span>
                                <span className="font-mm-data text-xs text-mm-text-muted">
                                  {toNumeric(q.default_points)} điểm
                                </span>
                              </div>

                              <MathCodeContent
                                content={q.question_text}
                                className="text-sm text-mm-heading"
                              />

                              <div className="grid grid-cols-1 gap-1.5 pt-1 sm:grid-cols-2">
                                {q.options.map((opt) => (
                                  <div
                                    key={opt.key}
                                    className={`flex items-start gap-2 rounded-mm-tag border px-2.5 py-1.5 text-xs ${
                                      opt.is_correct
                                        ? "border-mm-success/40 bg-mm-success-bg/60 text-mm-success"
                                        : "border-mm-divider bg-mm-bg text-mm-text-secondary"
                                    }`}
                                  >
                                    <span className="font-mm-mono font-medium">
                                      {opt.key}.
                                    </span>
                                    <MathCodeContent
                                      content={opt.text}
                                      inline
                                      className="text-xs text-inherit"
                                    />
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="flex shrink-0 items-center gap-1">
                              <button
                                type="button"
                                title="Chỉnh sửa câu hỏi"
                                onClick={() => {
                                  setEditingQuestion(q);
                                  setQuestionModalOpen(true);
                                }}
                                className="rounded-mm-tag p-2 text-mm-blue-hover hover:bg-mm-blue-light/30"
                              >
                                <Edit3 className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                title="Xóa câu hỏi"
                                onClick={() => setDeletingQuestion(q)}
                                className="rounded-mm-tag p-2 text-mm-danger hover:bg-mm-danger-bg"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </MmCard>
                </div>
              )}

              {activeTab === "quizzes" && (
                <div className="space-y-4">
                  {quizzes.length === 0 ? (
                    <MmCard variant="standard" className="py-12 text-center">
                      <ClipboardCheck className="mx-auto mb-3 h-10 w-10 text-mm-text-muted" />
                      <p className="font-mm-ui text-base text-mm-heading">
                        Chưa có kỳ thi nào trong môn học này
                      </p>
                      <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
                        Tạo đề thi theo ma trận bốc đề Snapshot để bắt đầu tổ chức kiểm tra.
                      </p>
                      <div className="mt-4">
                        <MmButton
                          variant="brand"
                          disabled={banks.length === 0}
                          onClick={() => setCreateQuizOpen(true)}
                        >
                          <Plus className="h-4 w-4" />
                          <span>Tạo đề thi đầu tiên</span>
                        </MmButton>
                      </div>
                    </MmCard>
                  ) : (
                    quizzes.map((quiz) => {
                      const statusMeta = QUIZ_STATUS_META[quiz.status];
                      return (
                        <MmCard
                          key={quiz.id}
                          variant="standard"
                          radius="card"
                          padding="lg"
                        >
                          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                            <div className="space-y-2.5">
                              <div className="flex flex-wrap items-center gap-2">
                                <span
                                  className={`inline-flex items-center rounded-full px-3 py-0.5 font-mm-ui text-xs font-medium ${statusMeta.className}`}
                                >
                                  {statusMeta.label}
                                </span>
                                <span className="inline-flex items-center gap-1 rounded-mm-tag bg-mm-divider px-2.5 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                                  <Clock className="h-3.5 w-3.5" />
                                  {quiz.time_limit_mins} phút · {quiz.question_count} câu
                                </span>
                                <span className="inline-flex items-center gap-1 rounded-mm-tag bg-mm-divider px-2.5 py-0.5 font-mm-ui text-xs text-mm-text-secondary">
                                  <ShieldCheck className="h-3.5 w-3.5" />
                                  {SECURITY_MODE_LABELS[quiz.security_mode]}
                                </span>
                                {quiz.has_passcode && (
                                  <span className="inline-flex items-center gap-1 rounded-mm-tag bg-mm-warning-bg px-2.5 py-0.5 font-mm-mono text-xs text-mm-warning">
                                    <KeyRound className="h-3.5 w-3.5" />
                                    Passcode: {quiz.passcode ?? "Đã đặt"}
                                  </span>
                                )}
                              </div>

                              <h2 className="font-mm-mid text-xl font-medium text-mm-heading">
                                {quiz.title}
                              </h2>

                              <div className="flex flex-wrap gap-x-6 gap-y-1 font-mm-ui text-xs text-mm-text-secondary">
                                <span>
                                  Mở đề: {formatDateTime(quiz.available_from)}
                                </span>
                                <span>
                                  Đóng đề: {formatDateTime(quiz.available_until)}
                                </span>
                                <span>
                                  Công bố điểm:{" "}
                                  {GRADE_RELEASE_LABELS[quiz.grade_release_policy]}
                                </span>
                                {quiz.ip_filter_range && (
                                  <span className="font-mm-mono">
                                    IP Lab: {quiz.ip_filter_range}
                                  </span>
                                )}
                                {quiz.grades_published_at && (
                                  <span className="text-mm-success">
                                    Đã công bố điểm lúc:{" "}
                                    {formatDateTime(quiz.grades_published_at)}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <MmButton
                                variant="secondary"
                                size="sm"
                                onClick={() => setSettingsQuiz(quiz)}
                              >
                                <Settings className="h-4 w-4" />
                                <span>Cấu hình phòng thi</span>
                              </MmButton>

                              {quiz.status === "DRAFT" && (
                                <MmButton
                                  variant="brand"
                                  size="sm"
                                  loading={publishingQuizId === quiz.id}
                                  onClick={() => handlePublishQuiz(quiz)}
                                >
                                  <Send className="h-4 w-4" />
                                  <span>Xuất bản đề</span>
                                </MmButton>
                              )}

                              {quiz.status !== "DRAFT" &&
                                !quiz.grades_published_at && (
                                  <MmButton
                                    variant="primary"
                                    size="sm"
                                    loading={publishingGradesId === quiz.id}
                                    onClick={() => handlePublishGrades(quiz)}
                                  >
                                    <Award className="h-4 w-4" />
                                    <span>Công bố điểm</span>
                                  </MmButton>
                                )}
                            </div>
                          </div>
                        </MmCard>
                      );
                    })
                  )}
                </div>
              )}

              {activeTab === "regrades" && (
                <MmCard variant="standard" radius="card" padding="none">
                  <div className="flex flex-col gap-3 border-b border-mm-divider px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="font-mm-mid text-lg font-medium text-mm-heading">
                        Danh sách đơn phúc khảo (cửa sổ 48 giờ)
                      </h2>
                      <p className="font-mm-ui text-xs text-mm-text-secondary">
                        Duyệt phúc khảo cá nhân hoặc Chấm lại toàn lớp khi đề gốc sai đáp án
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                      <select
                        aria-label="Chọn kỳ thi"
                        value={selectedRegradeQuizId}
                        onChange={(e) => setSelectedRegradeQuizId(e.target.value)}
                        className={`${mmInputClass(false)} w-64`}
                      >
                        {quizzes.length === 0 && (
                          <option value="">Chưa có kỳ thi</option>
                        )}
                        {quizzes.map((q) => (
                          <option key={q.id} value={q.id}>
                            {q.title}
                          </option>
                        ))}
                      </select>

                      <select
                        aria-label="Lọc trạng thái phúc khảo"
                        value={regradeStatusFilter}
                        onChange={(e) =>
                          setRegradeStatusFilter(e.target.value as RegradeStatus | "")
                        }
                        className={`${mmInputClass(false)} w-44`}
                      >
                        <option value="">Tất cả trạng thái</option>
                        <option value="PENDING">Chờ duyệt</option>
                        <option value="APPROVED">Đã chấp thuận</option>
                        <option value="REJECTED">Đã từ chối</option>
                      </select>
                    </div>
                  </div>

                  {loadingRegrades ? (
                    <div className="p-8 text-center font-mm-ui text-sm text-mm-text-muted">
                      Đang tải danh sách đơn phúc khảo...
                    </div>
                  ) : regrades.length === 0 ? (
                    <div className="p-12 text-center">
                      <CheckCircle2 className="mx-auto mb-3 h-9 w-9 text-mm-text-muted" />
                      <p className="font-mm-ui text-sm text-mm-text-secondary">
                        Không có đơn phúc khảo nào cho kỳ thi đã chọn.
                      </p>
                    </div>
                  ) : (
                    <div className="divide-y divide-mm-divider">
                      {regrades.map((req) => {
                        const statusMeta = REGRADE_STATUS_META[req.status];
                        return (
                          <div
                            key={req.id}
                            className="flex flex-col justify-between gap-4 px-6 py-4 sm:flex-row sm:items-start"
                          >
                            <div className="space-y-1.5">
                              <div className="flex flex-wrap items-center gap-2">
                                <span
                                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mm-ui text-xs font-medium ${statusMeta.className}`}
                                >
                                  {statusMeta.label}
                                </span>
                                <span className="rounded-mm-tag bg-mm-divider px-2 py-0.5 font-mm-ui text-xs text-mm-text-secondary">
                                  {REGRADE_SCOPE_LABELS[req.regrade_scope]}
                                </span>
                                <span className="font-mm-data text-xs text-mm-text-muted">
                                  Điểm cũ: {formatScore(req.old_score)}
                                  {req.new_score !== null &&
                                    req.new_score !== undefined &&
                                    ` -> Điểm mới: ${formatScore(req.new_score)}`}
                                </span>
                                <span className="font-mm-data text-xs text-mm-text-muted">
                                  Gửi lúc: {formatDateTime(req.created_at)}
                                </span>
                              </div>

                              <p className="font-mm-ui text-sm text-mm-heading">
                                {req.student_reason}
                              </p>

                              {req.reviewer_feedback && (
                                <p className="font-mm-ui text-xs text-mm-text-secondary">
                                  Phản hồi Giảng viên: {req.reviewer_feedback}
                                </p>
                              )}
                            </div>

                            {req.status === "PENDING" && (
                              <MmButton
                                variant="brand"
                                size="sm"
                                className="shrink-0"
                                onClick={() => setReviewingRegrade(req)}
                              >
                                Xử lý đơn
                              </MmButton>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </MmCard>
              )}
            </>
          ) : (
            <div className="space-y-4">
              {quizzes.length === 0 ? (
                <MmCard variant="standard" className="py-12 text-center">
                  <ClipboardCheck className="mx-auto mb-3 h-10 w-10 text-mm-text-muted" />
                  <p className="font-mm-ui text-base text-mm-heading">
                    Hiện chưa có kỳ thi nào được xuất bản trong môn học này.
                  </p>
                </MmCard>
              ) : (
                quizzes.map((quiz) => {
                  const statusMeta = QUIZ_STATUS_META[quiz.status];
                  const savedSubId = localStorage.getItem(
                    getLastSubmissionStorageKey(quiz.id)
                  );
                  return (
                    <MmCard
                      key={quiz.id}
                      variant="standard"
                      radius="card"
                      padding="lg"
                    >
                      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`inline-flex items-center rounded-full px-3 py-0.5 font-mm-ui text-xs font-medium ${statusMeta.className}`}
                            >
                              {statusMeta.label}
                            </span>
                            <span className="inline-flex items-center gap-1 rounded-mm-tag bg-mm-divider px-2.5 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                              <Clock className="h-3.5 w-3.5" />
                              {quiz.time_limit_mins} phút · {quiz.question_count} câu
                            </span>
                            {quiz.has_passcode && (
                              <span className="inline-flex items-center gap-1 rounded-mm-tag bg-mm-warning-bg px-2.5 py-0.5 font-mm-ui text-xs text-mm-warning">
                                <KeyRound className="h-3.5 w-3.5" />
                                Yêu cầu Passcode
                              </span>
                            )}
                          </div>

                          <h2 className="font-mm-mid text-xl font-medium text-mm-heading">
                            {quiz.title}
                          </h2>

                          <p className="font-mm-ui text-xs text-mm-text-secondary">
                            Khung giờ mở đề: {formatDateTime(quiz.available_from)} —{" "}
                            {formatDateTime(quiz.available_until)}
                          </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-2.5">
                          {savedSubId && (
                            <MmButton
                              variant="secondary"
                              onClick={() =>
                                navigate(
                                  `/courses/${course.id}/exams/${quiz.id}/result?submissionId=${savedSubId}`
                                )
                              }
                            >
                              <Award className="h-4 w-4" />
                              <span>Xem kết quả</span>
                            </MmButton>
                          )}
                          <MmButton
                            variant="brand"
                            onClick={() =>
                              navigate(`/courses/${course.id}/exams/${quiz.id}/take`)
                            }
                          >
                            <Play className="h-4 w-4" />
                            <span>Vào phòng thi</span>
                          </MmButton>
                        </div>
                      </div>
                    </MmCard>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}

      {course && isInstructor && (
        <>
          <QuestionFormModal
            open={questionModalOpen}
            courseId={course.id}
            banks={banks}
            learningObjectives={course.learning_objectives}
            editingQuestion={editingQuestion}
            defaultBankId={filterBankId || undefined}
            onClose={() => {
              setQuestionModalOpen(false);
              setEditingQuestion(null);
            }}
            onSaved={() => void loadInstructorData()}
          />

          <CreateQuizMatrixModal
            open={createQuizOpen}
            courseId={course.id}
            banks={banks}
            questions={questions}
            learningObjectives={course.learning_objectives}
            onClose={() => setCreateQuizOpen(false)}
            onCreated={() => void loadInstructorData()}
          />

          <QuizSecuritySettingsModal
            open={Boolean(settingsQuiz)}
            quiz={settingsQuiz}
            onClose={() => setSettingsQuiz(null)}
            onUpdated={() => void loadInstructorData()}
          />

          <RegradeReviewModal
            open={Boolean(reviewingRegrade)}
            regrade={reviewingRegrade}
            onClose={() => setReviewingRegrade(null)}
            onReviewed={() => void loadRegrades()}
          />

          <ConfirmModal
            open={Boolean(deletingQuestion)}
            title="Xóa câu hỏi khỏi ngân hàng?"
            description="Nếu câu hỏi đã từng được chụp Snapshot vào đề thi, hệ thống sẽ thực hiện xóa mềm để bảo toàn lịch sử đề thi (BR-EXAM-01)."
            confirmLabel="Xác nhận xóa"
            danger
            loading={deletingQuestionLoading}
            onConfirm={handleDeleteQuestion}
            onCancel={() => setDeletingQuestion(null)}
          />

          <ConfirmModal
            open={Boolean(deletingBank)}
            title={`Xóa danh mục "${deletingBank?.category_name ?? ""}"?`}
            description="Chỉ có thể xóa danh mục khi không còn câu hỏi hoạt động bên trong."
            confirmLabel="Xóa danh mục"
            danger
            loading={deletingBankLoading}
            onConfirm={handleDeleteBank}
            onCancel={() => setDeletingBank(null)}
          />
        </>
      )}
    </Layout>
  );
};
