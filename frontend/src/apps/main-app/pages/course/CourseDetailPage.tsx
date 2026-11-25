/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Archive,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  Edit3,
  FileCheck2,
  Lock,
  Plus,
  Save,
  Target,
  Trash2,
  Unlock,
  Users,
} from "lucide-react";
import { RichTextEditor } from "../../../../components/editors/RichTextEditor";
import { assessmentService } from "../../../../services/assessmentService";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import { useCourseContextStore } from "../../../../stores/courseContextStore";
import type { AssignmentSummaryItem } from "../../../../types/assessment";
import type { CourseDetail, CourseStatus, LOResponse } from "../../../../types/course";
import { BloomBadge } from "../../components/BloomBadge";
import { ConfirmModal } from "../../components/ConfirmModal";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { PillTabs, type PillTabItem } from "../../components/PillTabs";
import { RoleBadge } from "../../components/RoleBadge";
import { showToast } from "../../components/Toast";
import { StudentLayout } from "../../layouts/StudentLayout";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { CloneTemplateModal } from "./CloneTemplateModal";
import { LoFormModal } from "./LoFormModal";
import { StudentRosterPage } from "./StudentRosterPage";

type DetailTab = "syllabus" | "los" | "assignments" | "roster";

const STATUS_BADGE: Record<CourseStatus, { label: string; className: string }> = {
  UNPUBLISHED: {
    label: "Bản nháp",
    className: "bg-mm-btn-secondary text-mm-text-secondary",
  },
  PUBLISHED: {
    label: "Đang mở",
    className: "bg-mm-success-bg text-mm-success",
  },
  ENROLLMENT_CLOSED: {
    label: "Đóng ghi danh",
    className: "bg-mm-warning-bg text-mm-warning",
  },
  ARCHIVED: {
    label: "Đã lưu trữ (Chỉ đọc)",
    className: "bg-mm-divider text-mm-text-muted",
  },
};

export const CourseDetailPage: React.FC = () => {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const me = useAuthStore((s) => s.me);
  const setActiveCourse = useCourseContextStore((s) => s.setActiveCourse);

  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [assignments, setAssignments] = useState<AssignmentSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DetailTab>("syllabus");

  // Syllabus state
  const [name, setName] = useState("");
  const [credits, setCredits] = useState(3);
  const [syllabusHtml, setSyllabusHtml] = useState("");
  const [savingSyllabus, setSavingSyllabus] = useState(false);

  // Modals state
  const [importTplOpen, setImportTplOpen] = useState(false);
  const [loModalOpen, setLoModalOpen] = useState(false);
  const [editingLo, setEditingLo] = useState<LOResponse | null>(null);
  const [deletingLo, setDeletingLo] = useState<LOResponse | null>(null);
  const [deletingLoLoading, setDeletingLoLoading] = useState(false);
  const [reordering, setReordering] = useState(false);

  const [pendingStatusTarget, setPendingStatusTarget] = useState<CourseStatus | null>(null);
  const [transitioningStatus, setTransitioningStatus] = useState(false);

  const loadCourse = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    try {
      const detail = await courseService.getCourseDetail(courseId);
      setCourse(detail);
      setName(detail.name);
      setCredits(detail.credits);
      setSyllabusHtml(detail.syllabus_text ?? "");
      setActiveCourse({
        courseId: detail.id,
        role: detail.my_role ?? null,
        courseName: detail.name,
      });
      assessmentService
        .listCourseAssignments(courseId)
        .then((items) => setAssignments(items))
        .catch(() => setAssignments([]));
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải chi tiết môn học."
      );
    } finally {
      setLoading(false);
    }
  }, [courseId, setActiveCourse]);

  useEffect(() => {
    void loadCourse();
  }, [loadCourse]);

  const isInstructor =
    course?.my_role === "INSTRUCTOR" || me?.system_role === "ADMIN";
  const isArchived = course?.status === "ARCHIVED";
  const canEdit = isInstructor && !isArchived;

  const handleSaveSyllabus = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!course || !canEdit) return;
    if (name.trim().length < 3) {
      showToast("error", "Tên môn học phải có ít nhất 3 ký tự.");
      return;
    }

    setSavingSyllabus(true);
    try {
      const updated = await courseService.updateSyllabus(course.id, {
        name: name.trim(),
        credits,
        syllabus_text: syllabusHtml,
      });
      setCourse(updated);
      showToast("success", "Đã lưu đề cương môn học thành công!");
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể lưu đề cương môn học."
      );
    } finally {
      setSavingSyllabus(false);
    }
  };

  const handleStatusTransition = async () => {
    if (!course || !pendingStatusTarget) return;
    setTransitioningStatus(true);
    try {
      const updated = await courseService.transitionStatus(course.id, pendingStatusTarget);
      setCourse(updated);
      showToast("success", "Đã cập nhật trạng thái môn học.");
      setPendingStatusTarget(null);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể chuyển trạng thái môn học."
      );
    } finally {
      setTransitioningStatus(false);
    }
  };

  const handleDeleteLo = async () => {
    if (!course || !deletingLo) return;
    setDeletingLoLoading(true);
    try {
      await courseService.deleteLearningObjective(course.id, deletingLo.id);
      showToast("success", `Đã xóa chuẩn đầu ra ${deletingLo.code}.`);
      setDeletingLo(null);
      await loadCourse();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xóa chuẩn đầu ra."
      );
    } finally {
      setDeletingLoLoading(false);
    }
  };

  const handleMoveLo = async (index: number, direction: -1 | 1) => {
    if (!course || reordering) return;
    const list = [...course.learning_objectives];
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= list.length) return;

    const [moved] = list.splice(index, 1);
    list.splice(targetIdx, 0, moved);

    setCourse({ ...course, learning_objectives: list });
    setReordering(true);
    try {
      await courseService.reorderLearningObjectives(
        course.id,
        list.map((lo) => lo.id)
      );
      showToast("success", "Đã cập nhật thứ tự chuẩn đầu ra.");
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể thay đổi thứ tự chuẩn đầu ra."
      );
      await loadCourse();
    } finally {
      setReordering(false);
    }
  };

  const Layout = isInstructor ? TeacherLayout : StudentLayout;

  const tabs: PillTabItem<DetailTab>[] = [
    {
      value: "syllabus",
      label: "Đề cương",
      icon: <BookOpen className="h-4 w-4" />,
    },
    {
      value: "los",
      label: "Chuẩn đầu ra",
      count: course?.learning_objectives.length ?? 0,
      icon: <Target className="h-4 w-4" />,
    },
    {
      value: "assignments",
      label: "Bài tập & Đồ án",
      count: assignments.length,
      icon: <FileCheck2 className="h-4 w-4" />,
    },
    {
      value: "roster",
      label: "Danh sách lớp và Nhóm",
      count: course?.student_count ?? 0,
      icon: <Users className="h-4 w-4" />,
    },
  ];

  const statusConfirmCopy: Record<CourseStatus, { title: string; desc: string }> = {
    PUBLISHED: {
      title: "Xuất bản môn học?",
      desc: "Môn học sẽ được mở và sinh viên có thể tham gia bằng mã lớp (yêu cầu có ít nhất 1 Chuẩn đầu ra).",
    },
    ENROLLMENT_CLOSED: {
      title: "Đóng ghi danh tự động?",
      desc: "Sinh viên sẽ không thể tự vào lớp bằng mã Join Code cho tới khi bạn mở lại.",
    },
    ARCHIVED: {
      title: "Lưu trữ môn học vĩnh viễn?",
      desc: "Sau khi lưu trữ, toàn bộ đề cương, chuẩn đầu ra và danh sách lớp sẽ chuyển sang chế độ chỉ đọc.",
    },
    UNPUBLISHED: {
      title: "Chuyển về bản nháp?",
      desc: "Môn học sẽ chuyển sang trạng thái bản nháp.",
    },
  };

  return (
    <Layout>
      {loading ? (
        <div className="space-y-4">
          <div className="h-10 w-64 animate-pulse rounded-mm-btn bg-mm-divider" />
          <div className="h-72 animate-pulse rounded-mm-card bg-mm-divider/60" />
        </div>
      ) : !course ? (
        <MmCard variant="standard" className="py-12 text-center">
          <p className="font-mm-ui text-base text-mm-text-secondary">
            Không tìm thấy môn học yêu cầu hoặc bạn không có quyền truy cập.
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
              to="/courses"
              className="mb-3 inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Môn học của tôi</span>
            </Link>

            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
              <div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="rounded-mm-tag bg-mm-divider px-2.5 py-0.5 font-mm-data text-xs font-medium text-mm-text-secondary">
                    {course.course_code} · {course.section_code}
                  </span>
                  <span className="font-mm-data text-xs text-mm-text-muted">
                    {course.semester} · {course.credits} tín chỉ
                  </span>
                  <RoleBadge role={course.my_role} />
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-0.5 font-mm-ui text-xs font-medium ${STATUS_BADGE[course.status].className}`}
                  >
                    {STATUS_BADGE[course.status].label}
                  </span>
                  {course.is_template && (
                    <span className="inline-flex items-center rounded-full bg-mm-dark px-3 py-0.5 font-mm-ui text-xs font-medium text-white">
                      Môn mẫu
                    </span>
                  )}
                </div>

                <h1 className="font-mm-display text-[31px] font-semibold tracking-tight text-mm-heading">
                  {course.name}
                </h1>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/courses/${course.id}/exams`}>
                  <MmButton variant="secondary">
                    <ClipboardCheck className="h-4 w-4" />
                    <span>Ngân hàng đề & Khảo thí</span>
                  </MmButton>
                </Link>

                {canEdit && !course.is_template && (
                  <>
                    {course.status === "UNPUBLISHED" && (
                      <MmButton
                        variant="brand"
                        onClick={() => setPendingStatusTarget("PUBLISHED")}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Xuất bản môn học</span>
                      </MmButton>
                    )}
                    {course.status === "PUBLISHED" && (
                      <MmButton
                        variant="secondary"
                        onClick={() => setPendingStatusTarget("ENROLLMENT_CLOSED")}
                      >
                        <Lock className="h-4 w-4" />
                        <span>Đóng ghi danh</span>
                      </MmButton>
                    )}
                    {course.status === "ENROLLMENT_CLOSED" && (
                      <MmButton
                        variant="secondary"
                        onClick={() => setPendingStatusTarget("PUBLISHED")}
                      >
                        <Unlock className="h-4 w-4" />
                        <span>Mở lại ghi danh</span>
                      </MmButton>
                    )}
                    {(course.status === "PUBLISHED" ||
                      course.status === "ENROLLMENT_CLOSED") && (
                      <MmButton
                        variant="ghost"
                        onClick={() => setPendingStatusTarget("ARCHIVED")}
                      >
                        <Archive className="h-4 w-4" />
                        <span>Lưu trữ môn</span>
                      </MmButton>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          <PillTabs items={tabs} value={activeTab} onChange={setActiveTab} />

          {activeTab === "syllabus" && (
            <MmCard variant="standard" radius="card" padding="lg">
              <div className="mb-6 flex flex-col justify-between gap-3 border-b border-mm-divider pb-4 sm:flex-row sm:items-center">
                <div>
                  <h2 className="font-mm-mid text-[24px] font-medium text-mm-heading">
                    Đề cương chi tiết môn học
                  </h2>
                  <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
                    Thông tin học phần, số tín chỉ và nội dung đề cương giảng dạy
                  </p>
                </div>

                {canEdit && (
                  <MmButton
                    variant="secondary"
                    onClick={() => setImportTplOpen(true)}
                  >
                    <Copy className="h-4 w-4" />
                    <span>Nạp từ Môn mẫu</span>
                  </MmButton>
                )}
              </div>

              <form onSubmit={handleSaveSyllabus} className="space-y-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-6">
                  <div className="sm:col-span-3">
                    <FormField label="Tên môn học" htmlFor="syllabus-name" required>
                      <input
                        id="syllabus-name"
                        type="text"
                        disabled={!canEdit}
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className={mmInputClass(false)}
                      />
                    </FormField>
                  </div>

                  <div className="sm:col-span-2">
                    <FormField label="Mã học phần" htmlFor="syllabus-course-code" required>
                      <input
                        id="syllabus-course-code"
                        type="text"
                        disabled
                        value={course.course_code}
                        className={`${mmInputClass(false)} bg-mm-divider/60 font-mm-mono text-mm-text-secondary`}
                      />
                    </FormField>
                  </div>

                  <div className="sm:col-span-1">
                    <FormField label="Số tín chỉ" htmlFor="syllabus-credits" required>
                      <input
                        id="syllabus-credits"
                        type="number"
                        min={1}
                        max={6}
                        disabled={!canEdit}
                        value={credits}
                        onChange={(e) => setCredits(Number(e.target.value))}
                        className={mmInputClass(false)}
                      />
                    </FormField>
                  </div>
                </div>

                <FormField label="Nội dung đề cương và mục tiêu môn học">
                  <RichTextEditor
                    value={syllabusHtml}
                    onChange={setSyllabusHtml}
                    readOnly={!canEdit}
                  />
                </FormField>

                {canEdit && (
                  <div className="flex justify-end pt-2">
                    <MmButton
                      type="submit"
                      variant="brand"
                      loading={savingSyllabus}
                    >
                      <Save className="h-4 w-4" />
                      <span>Lưu đề cương</span>
                    </MmButton>
                  </div>
                )}
              </form>
            </MmCard>
          )}

          {activeTab === "los" && (
            <MmCard variant="standard" radius="card" padding="none">
              <div className="flex flex-col justify-between gap-3 border-b border-mm-divider px-6 py-5 sm:flex-row sm:items-center">
                <div>
                  <h2 className="font-mm-mid text-[24px] font-medium text-mm-heading">
                    Danh mục Chuẩn đầu ra (LO)
                  </h2>
                  <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
                    Quản lý các chuẩn đầu ra học phần theo thang nhận thức Bloom
                  </p>
                </div>

                {canEdit && (
                  <MmButton
                    variant="brand"
                    onClick={() => {
                      setEditingLo(null);
                      setLoModalOpen(true);
                    }}
                  >
                    <Plus className="h-4 w-4" />
                    <span>Thêm chuẩn đầu ra</span>
                  </MmButton>
                )}
              </div>

              {course.learning_objectives.length === 0 ? (
                <div className="p-12 text-center">
                  <Target className="mx-auto mb-3 h-9 w-9 text-mm-text-muted" />
                  <p className="font-mm-ui text-sm text-mm-text-secondary">
                    Môn học chưa có chuẩn đầu ra nào. Cần ít nhất 1 LO trước khi xuất bản.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left">
                    <thead>
                      <tr className="border-b border-mm-divider bg-mm-divider/40 font-mm-ui text-xs font-medium text-mm-text-secondary">
                        <th className="px-6 py-3">STT</th>
                        <th className="px-6 py-3">Mã LO</th>
                        <th className="px-6 py-3">Tên chuẩn đầu ra</th>
                        <th className="px-6 py-3">Mức Bloom</th>
                        <th className="px-6 py-3">Trọng số (%)</th>
                        {canEdit && <th className="px-6 py-3 text-right">Thao tác</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-mm-divider font-mm-ui text-sm">
                      {course.learning_objectives.map((lo, idx) => (
                        <tr key={lo.id} className="hover:bg-mm-divider/20">
                          <td className="px-6 py-3.5 font-mm-data text-xs text-mm-text-muted">
                            {idx + 1}
                          </td>
                          <td className="px-6 py-3.5 font-mm-mono text-xs font-medium text-mm-heading">
                            {lo.code}
                          </td>
                          <td className="px-6 py-3.5 text-mm-heading">
                            <p>{lo.description}</p>
                            {lo.detail_description && (
                              <p className="mt-0.5 text-xs text-mm-text-helper">
                                {lo.detail_description}
                              </p>
                            )}
                          </td>
                          <td className="px-6 py-3.5">
                            <BloomBadge level={lo.bloom_level} />
                          </td>
                          <td className="px-6 py-3.5 font-mm-data text-xs text-mm-text-secondary">
                            {lo.weight_percent !== null && lo.weight_percent !== undefined
                              ? `${lo.weight_percent}%`
                              : "—"}
                          </td>
                          {canEdit && (
                            <td className="px-6 py-3.5 text-right">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  type="button"
                                  title="Di chuyển lên"
                                  disabled={idx === 0 || reordering}
                                  onClick={() => handleMoveLo(idx, -1)}
                                  className="rounded-mm-tag p-1.5 text-mm-text-secondary hover:bg-mm-divider disabled:opacity-30"
                                >
                                  <ArrowUp className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  title="Di chuyển xuống"
                                  disabled={
                                    idx === course.learning_objectives.length - 1 ||
                                    reordering
                                  }
                                  onClick={() => handleMoveLo(idx, 1)}
                                  className="rounded-mm-tag p-1.5 text-mm-text-secondary hover:bg-mm-divider disabled:opacity-30"
                                >
                                  <ArrowDown className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  title="Chỉnh sửa"
                                  onClick={() => {
                                    setEditingLo(lo);
                                    setLoModalOpen(true);
                                  }}
                                  className="rounded-mm-tag p-1.5 text-mm-blue-hover hover:bg-mm-blue-light/30"
                                >
                                  <Edit3 className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  title="Xóa chuẩn đầu ra"
                                  onClick={() => setDeletingLo(lo)}
                                  className="rounded-mm-tag p-1.5 text-mm-danger hover:bg-mm-danger-bg"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </MmCard>
          )}

          {activeTab === "assignments" && (
            <MmCard variant="standard" className="space-y-4">
              <div className="flex items-center justify-between border-b border-mm-divider pb-3">
                <div>
                  <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
                    Danh sách Bài tập & Đồ án
                  </h2>
                  <p className="font-mm-ui text-xs text-mm-text-muted">
                    Truy cập nhiệm vụ học tập, nộp sản phẩm, khai báo AI và tham gia vấn đáp Viva Sandbox
                  </p>
                </div>
              </div>
              {assignments.length === 0 ? (
                <p className="py-8 text-center font-mm-ui text-sm text-mm-text-muted">
                  Chưa có bài tập nào được giao trong môn học này.
                </p>
              ) : (
                <div className="grid gap-3">
                  {assignments.map((item) => (
                    <Link
                      key={item.id}
                      to={`/courses/${course.id}/assignments/${item.id}`}
                      className="flex flex-col justify-between gap-3 rounded-mm-card border border-mm-divider bg-white p-4 transition-colors hover:border-mm-primary sm:flex-row sm:items-center"
                    >
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mm-display text-base font-semibold text-mm-heading">
                            {item.title}
                          </span>
                          {item.is_viva_required && (
                            <span className="rounded-full bg-[#eff6ff] px-2.5 py-0.5 font-mm-ui text-xs font-medium text-[#1e40af]">
                              Viva ({item.viva_question_count} câu)
                            </span>
                          )}
                        </div>
                        <p className="font-mm-data text-xs text-mm-text-secondary">
                          Hạn nộp: {new Date(item.due_date).toLocaleString("vi-VN")} · Đã nộp: {item.submission_count} phiên bản
                          {item.latest_status ? ` · Trạng thái: ${item.latest_status}` : ""}
                        </p>
                      </div>
                      <MmButton variant="secondary" size="sm">
                        <span>Mở bài tập</span>
                      </MmButton>
                    </Link>
                  ))}
                </div>
              )}
            </MmCard>
          )}

          {activeTab === "roster" && (
            <StudentRosterPage
              courseIdProp={course.id}
              courseProp={course}
              embedded
              onCourseUpdated={(updated) => setCourse(updated)}
            />
          )}
        </div>
      )}

      {course && (
        <>
          <CloneTemplateModal
            open={importTplOpen}
            mode="import-into-course"
            targetCourseId={course.id}
            onClose={() => setImportTplOpen(false)}
            onImportedSyllabus={() => void loadCourse()}
          />

          <LoFormModal
            open={loModalOpen}
            courseId={course.id}
            editingLo={editingLo}
            onClose={() => {
              setLoModalOpen(false);
              setEditingLo(null);
            }}
            onSaved={() => void loadCourse()}
          />

          <ConfirmModal
            open={Boolean(deletingLo)}
            title={`Xóa chuẩn đầu ra ${deletingLo?.code ?? ""}?`}
            description="Chuẩn đầu ra sẽ bị xóa khỏi môn học nếu chưa được tham chiếu bởi học liệu hoặc bài kiểm tra (BR-LO-01)."
            confirmLabel="Xóa chuẩn đầu ra"
            danger
            loading={deletingLoLoading}
            onConfirm={handleDeleteLo}
            onCancel={() => setDeletingLo(null)}
          />

          <ConfirmModal
            open={Boolean(pendingStatusTarget)}
            title={
              pendingStatusTarget ? statusConfirmCopy[pendingStatusTarget].title : ""
            }
            description={
              pendingStatusTarget ? statusConfirmCopy[pendingStatusTarget].desc : ""
            }
            confirmLabel="Xác nhận"
            danger={pendingStatusTarget === "ARCHIVED"}
            loading={transitioningStatus}
            onConfirm={handleStatusTransition}
            onCancel={() => setPendingStatusTarget(null)}
          />
        </>
      )}
    </Layout>
  );
};
