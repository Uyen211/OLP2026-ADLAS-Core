/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  Bell,
  BellOff,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  History,
  Lock,
  RefreshCw,
  Settings2,
  ShieldAlert,
  Unlock,
} from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { gradebookService } from "../../../../services/gradebookService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import type { CourseDetail } from "../../../../types/course";
import type {
  ClassGradebookOverviewResponse,
  GradeAuditLogItem,
  GradebookStructureResponse,
  GradeColumnItem,
  PostGradesScope,
  StudentMyGradesResponse,
} from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { showToast } from "../../components/Toast";
import { StudentLayout } from "../../layouts/StudentLayout";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { GradebookLockModal } from "./GradebookLockModal";
import { GradebookStructureModal } from "./GradebookStructureModal";
import { GradeDistributionModal } from "./GradeDistributionModal";

export const GradebookPage: React.FC = () => {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const me = useAuthStore((s) => s.me);

  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [overview, setOverview] = useState<ClassGradebookOverviewResponse | null>(null);
  const [structure, setStructure] = useState<GradebookStructureResponse | null>(null);
  const [myGrades, setMyGrades] = useState<StudentMyGradesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Modals
  const [structureOpen, setStructureOpen] = useState(false);
  const [distributionOpen, setDistributionOpen] = useState(false);
  const [lockModalMode, setLockModalMode] = useState<"lock" | "unlock" | null>(null);
  const [postingCol, setPostingCol] = useState<GradeColumnItem | null>(null);
  const [postScope, setPostScope] = useState<PostGradesScope>("ALL");
  const [postNotify, setPostNotify] = useState(true);
  const [postingBusy, setPostingBusy] = useState(false);

  // Inline manual score editing
  const [editingCell, setEditingCell] = useState<{
    columnId: string;
    userId: string;
    value: string;
  } | null>(null);
  const [savingCell, setSavingCell] = useState(false);

  // Audit logs
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditLogs, setAuditLogs] = useState<GradeAuditLogItem[]>([]);

  const isInstructor =
    course?.my_role === "INSTRUCTOR" || me?.system_role === "ADMIN";

  const loadData = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    try {
      const detail = await courseService.getCourseDetail(courseId);
      setCourse(detail);
      const instructorRole =
        detail.my_role === "INSTRUCTOR" || me?.system_role === "ADMIN";
      if (instructorRole) {
        const [ov, st] = await Promise.all([
          gradebookService.getClassOverview(courseId),
          gradebookService.getStructure(courseId),
        ]);
        setOverview(ov);
        setStructure(st);
      } else {
        const mine = await gradebookService.getStudentMyGrades(courseId);
        setMyGrades(mine);
      }
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải dữ liệu sổ điểm môn học."
      );
    } finally {
      setLoading(false);
    }
  }, [courseId, me?.system_role]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSyncItems = async () => {
    setSyncing(true);
    try {
      const res = await gradebookService.syncCourseItems(courseId);
      showToast(
        "success",
        `Đã đồng bộ ${res.synced_assignments} cột bài tập mới vào Sổ điểm.`
      );
      await loadData();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể đồng bộ cột điểm.");
    } finally {
      setSyncing(false);
    }
  };

  const handlePostGradesConfirm = async () => {
    if (!postingCol) return;
    setPostingBusy(true);
    try {
      const res = await gradebookService.postColumnGrades(
        courseId,
        postingCol.id,
        postScope,
        postNotify
      );
      showToast(
        "success",
        `Đã công bố điểm cho cột "${postingCol.title}" (${res.published_grades_count} bài đã chấm).`
      );
      setPostingCol(null);
      await loadData();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể công bố điểm.");
    } finally {
      setPostingBusy(false);
    }
  };

  const handleSaveManualScore = async () => {
    if (!editingCell) return;
    const parsed = Number(editingCell.value);
    if (Number.isNaN(parsed) || parsed < 0 || parsed > 10) {
      showToast("error", "Điểm số phải là giá trị từ 0.0 đến 10.0 (E-GB-02).");
      return;
    }
    setSavingCell(true);
    try {
      await gradebookService.upsertManualGrade(courseId, editingCell.columnId, {
        user_id: editingCell.userId,
        official_score: parsed,
      });
      showToast("success", "Đã cập nhật điểm số thành công.");
      setEditingCell(null);
      await loadData();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể lưu điểm.");
    } finally {
      setSavingCell(false);
    }
  };

  const handleOpenAuditLogs = async () => {
    setAuditOpen(true);
    try {
      const logs = await gradebookService.listAuditLogs(courseId);
      setAuditLogs(logs);
    } catch {
      setAuditLogs([]);
    }
  };

  const Layout = isInstructor ? TeacherLayout : StudentLayout;
  const allColumns: GradeColumnItem[] = overview
    ? overview.groups.flatMap((g) => g.columns)
    : [];

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <Link
              to={`/courses/${courseId}`}
              className="mb-2 inline-flex items-center gap-1.5 text-sm font-medium text-mm-text-secondary hover:text-mm-heading"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Quay lại môn học</span>
            </Link>
            <h1 className="font-mm-display text-2xl font-bold text-mm-heading">
              {isInstructor ? "Sổ Điểm Tổng Hợp & SpeedGrader" : "Bảng Điểm Cá Nhân"}
            </h1>
            {course && (
              <p className="mt-1 text-xs text-mm-text-secondary">
                {course.course_code} · {course.section_code} — {course.name}
              </p>
            )}
          </div>

          {isInstructor && overview && (
            <div className="flex flex-wrap items-center gap-2">
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => setStructureOpen(true)}
                disabled={overview.is_locked}
              >
                <Settings2 className="h-4 w-4" />
                <span>Cấu hình Sổ điểm</span>
              </MmButton>
              <MmButton
                variant="secondary"
                size="sm"
                loading={syncing}
                disabled={overview.is_locked}
                onClick={handleSyncItems}
              >
                <RefreshCw className="h-4 w-4" />
                <span>Đồng bộ Bài tập</span>
              </MmButton>
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => setDistributionOpen(true)}
              >
                <BarChart3 className="h-4 w-4" />
                <span>Phổ điểm</span>
              </MmButton>
              <MmButton variant="secondary" size="sm" onClick={handleOpenAuditLogs}>
                <History className="h-4 w-4" />
                <span>Nhật ký kiểm toán</span>
              </MmButton>
              {overview.is_locked ? (
                <MmButton
                  variant="secondary"
                  size="sm"
                  onClick={() => setLockModalMode("unlock")}
                >
                  <Unlock className="h-4 w-4 text-amber-600" />
                  <span>Yêu cầu mở khóa</span>
                </MmButton>
              ) : (
                <MmButton
                  variant="danger"
                  size="sm"
                  onClick={() => setLockModalMode("lock")}
                >
                  <Lock className="h-4 w-4" />
                  <span>Khóa Niêm Phong</span>
                </MmButton>
              )}
            </div>
          )}
        </div>

        {/* Locked Banner */}
        {overview?.is_locked && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900">
            <span className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-amber-700" />
              SỔ ĐIỂM ĐÃ ĐƯỢC NIÊM PHONG (Chỉ đọc — Khóa bởi{" "}
              {overview.locked_by_name || "Giảng viên"} lúc{" "}
              {overview.locked_at ? new Date(overview.locked_at).toLocaleString("vi-VN") : ""})
            </span>
            <span className="font-normal">Mọi thao tác sửa điểm bị chặn (E-14).</span>
          </div>
        )}

        {loading ? (
          <MmCard variant="standard" className="py-16 text-center text-sm text-mm-text-secondary">
            Đang tải dữ liệu sổ điểm...
          </MmCard>
        ) : isInstructor && overview ? (
          <>
            {/* Summary KPI Cards */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Tổng sinh viên</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-mm-heading">
                  {overview.total_students}
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Đạt môn</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-emerald-700">
                  {overview.passed_count} ({overview.pass_rate_pct}%)
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Rớt môn</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-rose-700">
                  {overview.failed_count} ({overview.fail_rate_pct}%)
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Trượt Điểm liệt (Hurdle)</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-rose-600">
                  {overview.hurdle_failed_count}
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Điểm TB Lớp (Hệ 10)</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-blue-700">
                  {overview.class_average_10 ?? "--"}
                </p>
              </MmCard>
            </div>

            {overview.incomplete_students_count > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-2.5 text-xs text-amber-900">
                Còn <strong>{overview.incomplete_students_count}</strong> sinh viên chưa nhập đủ điểm
                thành phần (E-CALC-01 — Điểm tổng kết đang hiển thị kèm dấu * tạm tính).
              </div>
            )}

            {/* Main Gradebook Matrix */}
            <MmCard variant="standard" padding="none">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-mm-divider bg-slate-50 text-mm-text-secondary">
                      <th className="sticky left-0 z-10 bg-slate-50 px-4 py-3 font-semibold">
                        Sinh viên
                      </th>
                      {allColumns.map((col) => (
                        <th key={col.id} className="min-w-[150px] px-3 py-3 font-semibold">
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center justify-between gap-1">
                              <span className="truncate text-mm-heading" title={col.title}>
                                {col.title}
                              </span>
                              {col.is_muted ? (
                                <button
                                  type="button"
                                  disabled={overview.is_locked}
                                  onClick={() => setPostingCol(col)}
                                  title="Đang ẩn điểm (Muted) — Bấm để công bố điểm"
                                  className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-700 hover:bg-blue-100 hover:text-blue-700"
                                >
                                  <BellOff className="h-3 w-3" />
                                  <span>Ẩn</span>
                                </button>
                              ) : (
                                <span
                                  title="Đã công bố điểm cho sinh viên"
                                  className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800"
                                >
                                  <Bell className="h-3 w-3" />
                                  <span>Mở</span>
                                </span>
                              )}
                            </div>
                            {col.item_type === "ASSIGNMENT" && col.item_id && (
                              <Link
                                to={`/courses/${courseId}/assignments/${col.item_id}/speedgrader`}
                                className="inline-flex items-center gap-1 text-[10px] font-medium text-blue-600 hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" />
                                <span>Mở SpeedGrader</span>
                              </Link>
                            )}
                          </div>
                        </th>
                      ))}
                      <th className="px-3 py-3 font-semibold">Hệ 10</th>
                      <th className="px-3 py-3 font-semibold">Hurdle</th>
                      <th className="px-3 py-3 font-semibold">Điểm chữ</th>
                      <th className="px-3 py-3 font-semibold">Hệ 4</th>
                      <th className="px-3 py-3 font-semibold">Kết quả</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mm-divider">
                    {overview.students.length === 0 ? (
                      <tr>
                        <td
                          colSpan={allColumns.length + 6}
                          className="px-6 py-10 text-center text-sm text-mm-text-muted"
                        >
                          Chưa có sinh viên nào trong lớp học phần này.
                        </td>
                      </tr>
                    ) : (
                      overview.students.map((stu) => (
                        <tr
                          key={stu.user_id}
                          className={
                            stu.hurdle_failed
                              ? "bg-rose-50/70 hover:bg-rose-50"
                              : "hover:bg-slate-50/60"
                          }
                        >
                          <td className="sticky left-0 z-10 bg-inherit px-4 py-3">
                            <p className="font-semibold text-mm-heading">{stu.full_name}</p>
                            <p className="font-mm-mono text-[11px] text-mm-text-muted">
                              {stu.user_code || stu.email}
                            </p>
                          </td>
                          {allColumns.map((col) => {
                            const cell = stu.column_grades[col.id];
                            const isEditing =
                              editingCell?.columnId === col.id &&
                              editingCell?.userId === stu.user_id;
                            const hasScore =
                              cell?.official_score !== null &&
                              cell?.official_score !== undefined;

                            return (
                              <td key={col.id} className="px-3 py-3">
                                {isEditing ? (
                                  <div className="flex items-center gap-1">
                                    <input
                                      type="number"
                                      step="0.1"
                                      min={0}
                                      max={10}
                                      autoFocus
                                      value={editingCell.value}
                                      onChange={(e) =>
                                        setEditingCell({ ...editingCell, value: e.target.value })
                                      }
                                      className="w-16 rounded border border-blue-400 px-1.5 py-1 font-mm-mono text-xs"
                                    />
                                    <button
                                      type="button"
                                      disabled={savingCell}
                                      onClick={handleSaveManualScore}
                                      className="rounded bg-blue-600 px-2 py-1 text-[10px] font-semibold text-white"
                                    >
                                      Lưu
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setEditingCell(null)}
                                      className="rounded bg-slate-200 px-1.5 py-1 text-[10px] text-slate-700"
                                    >
                                      Hủy
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    type="button"
                                    title={
                                      overview.is_locked
                                        ? "Sổ điểm đã khóa niêm phong (E-14)"
                                        : "Nhấp để nhập hoặc sửa điểm trực tiếp"
                                    }
                                    onClick={() => {
                                      if (overview.is_locked) {
                                        showToast(
                                          "error",
                                          "Sổ điểm đã bị khóa niêm phong. Không thể chỉnh sửa trực tiếp (E-14)."
                                        );
                                        return;
                                      }
                                      setEditingCell({
                                        columnId: col.id,
                                        userId: stu.user_id,
                                        value: hasScore ? String(cell.official_score) : "",
                                      });
                                    }}
                                    className={`inline-flex min-w-[60px] items-center justify-center rounded-lg border px-2 py-1 font-mm-mono text-xs ${
                                      overview.is_locked
                                        ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-500"
                                        : hasScore
                                          ? "border-slate-200 bg-white text-mm-heading hover:border-blue-400"
                                          : "border-amber-300 bg-amber-50 text-amber-800"
                                    }`}
                                  >
                                    {hasScore ? cell.official_score : "(-)"}
                                  </button>
                                )}
                                {cell?.evidence_flag === "CONFLICTING" && (
                                  <span className="ml-1 inline-block rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">
                                    Mâu thuẫn
                                  </span>
                                )}
                              </td>
                            );
                          })}
                          <td className="px-3 py-3 font-mm-mono font-bold text-mm-heading">
                            {stu.final_score_10 !== null && stu.final_score_10 !== undefined
                              ? `${stu.final_score_10}${stu.is_provisional ? "*" : ""}`
                              : "--"}
                          </td>
                          <td className="px-3 py-3">
                            {stu.hurdle_failed ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-800">
                                <ShieldAlert className="h-3 w-3" />
                                Trượt Điểm Liệt
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                                <CheckCircle2 className="h-3 w-3" />
                                Đạt
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-3 font-mm-mono font-bold">
                            {stu.letter_grade ?? "--"}
                          </td>
                          <td className="px-3 py-3 font-mm-mono">{stu.score_4 ?? "--"}</td>
                          <td className="px-3 py-3">
                            {stu.is_passed === true ? (
                              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-semibold text-emerald-800">
                                Đạt môn
                              </span>
                            ) : stu.is_passed === false ? (
                              <span className="rounded-full bg-rose-100 px-2.5 py-0.5 font-semibold text-rose-800">
                                Rớt môn
                              </span>
                            ) : (
                              <span className="text-mm-text-muted">Chưa đủ</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </MmCard>
          </>
        ) : myGrades ? (
          /* Student Read-Only View (Strictly enforces BR-09 Muted Policy) */
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Điểm Hệ 10</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-mm-heading">
                  {myGrades.final_score_10 ?? "--"}
                  {myGrades.is_provisional ? "*" : ""}
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Điểm Chữ (TT 08)</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-blue-700">
                  {myGrades.letter_grade ?? "--"}
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Điểm Hệ 4</p>
                <p className="mt-1 font-mm-mono text-xl font-bold text-mm-heading">
                  {myGrades.score_4 ?? "--"}
                </p>
              </MmCard>
              <MmCard variant="standard" padding="sm">
                <p className="text-xs text-mm-text-muted">Kết quả</p>
                <p className="mt-1 text-base font-bold text-mm-heading">
                  {myGrades.hurdle_failed
                    ? "Rớt (Điểm liệt)"
                    : myGrades.is_passed === true
                      ? "Đạt môn"
                      : myGrades.is_passed === false
                        ? "Rớt môn"
                        : "Đang cập nhật"}
                </p>
              </MmCard>
            </div>

            <MmCard variant="standard" padding="none">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-mm-divider bg-slate-50 text-xs font-semibold text-mm-text-secondary">
                    <th className="px-5 py-3">Nhóm điểm</th>
                    <th className="px-5 py-3">Cột điểm</th>
                    <th className="px-5 py-3">Điểm số</th>
                    <th className="px-5 py-3">Trạng thái & Nhận xét</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mm-divider">
                  {myGrades.items.map((item) => (
                    <tr key={item.column_id}>
                      <td className="px-5 py-3 text-xs text-mm-text-secondary">
                        {item.group_name} ({item.weight_percent}%)
                      </td>
                      <td className="px-5 py-3 font-medium text-mm-heading">{item.title}</td>
                      <td className="px-5 py-3 font-mm-mono font-semibold">
                        {item.is_muted ? "--" : (item.official_score ?? "--")}
                      </td>
                      <td className="px-5 py-3 text-xs text-mm-text-secondary">
                        {item.is_muted ? (
                          <span className="italic text-amber-700">{item.status_label}</span>
                        ) : (
                          <div className="space-y-1">
                            <span>{item.instructor_feedback || item.status_label}</span>
                            {item.voice_feedback_url && (
                              <audio controls className="h-8 max-w-xs" src={item.voice_feedback_url} />
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </MmCard>
          </div>
        ) : null}
      </div>

      {/* Post Grades Modal (T2-P-M5-05 Branch 1) */}
      {postingCol && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-md rounded-2xl border border-mm-border bg-white p-6 shadow-xl space-y-4">
            <h3 className="font-mm-display text-lg font-semibold text-mm-heading">
              Công bố điểm cột &quot;{postingCol.title}&quot;
            </h3>
            <div className="space-y-2 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={postScope === "ALL"}
                  onChange={() => setPostScope("ALL")}
                />
                <span>Công bố cho tất cả sinh viên trong lớp</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={postScope === "GRADED_ONLY"}
                  onChange={() => setPostScope("GRADED_ONLY")}
                />
                <span>Chỉ công bố cho những bài đã chấm xong</span>
              </label>
              <label className="mt-3 flex items-center gap-2 text-xs text-mm-text-secondary">
                <input
                  type="checkbox"
                  checked={postNotify}
                  onChange={(e) => setPostNotify(e.target.checked)}
                />
                <span>Gửi thông báo tự động đến ứng dụng/email của sinh viên</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-mm-divider pt-4">
              <MmButton variant="secondary" onClick={() => setPostingCol(null)}>
                <span>Hủy</span>
              </MmButton>
              <MmButton variant="brand" loading={postingBusy} onClick={handlePostGradesConfirm}>
                <span>Xác nhận Công Bố</span>
              </MmButton>
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Modal */}
      {auditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
          <div className="max-h-[80vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-mm-border bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-mm-divider pb-3">
              <h3 className="flex items-center gap-2 font-mm-display text-lg font-semibold text-mm-heading">
                <ClipboardList className="h-5 w-5 text-blue-600" />
                Nhật ký Kiểm toán Sổ điểm (Audit Trail)
              </h3>
              <MmButton variant="secondary" size="sm" onClick={() => setAuditOpen(false)}>
                <span>Đóng</span>
              </MmButton>
            </div>
            {auditLogs.length === 0 ? (
              <p className="py-8 text-center text-sm text-mm-text-muted">
                Chưa có sự kiện kiểm toán nào.
              </p>
            ) : (
              <div className="space-y-2">
                {auditLogs.map((log) => (
                  <div
                    key={log.id}
                    className="rounded-xl border border-mm-divider bg-slate-50 p-3 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mm-mono font-bold text-blue-700">
                        {log.action_type}
                      </span>
                      <span className="font-mm-mono text-[11px] text-mm-text-muted">
                        {new Date(log.created_at).toLocaleString("vi-VN")}
                      </span>
                    </div>
                    {log.reason && (
                      <p className="mt-1 text-mm-heading">
                        <strong>Lý do:</strong> {log.reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <GradebookStructureModal
        open={structureOpen}
        courseId={courseId}
        structure={structure}
        onClose={() => setStructureOpen(false)}
        onSaved={() => void loadData()}
      />

      {overview && (
        <GradeDistributionModal
          open={distributionOpen}
          buckets={overview.distribution}
          passRatePct={overview.pass_rate_pct}
          failRatePct={overview.fail_rate_pct}
          classAverage10={overview.class_average_10}
          onClose={() => setDistributionOpen(false)}
        />
      )}

      <GradebookLockModal
        open={lockModalMode !== null}
        mode={lockModalMode ?? "lock"}
        courseId={courseId}
        onClose={() => setLockModalMode(null)}
        onSuccess={() => void loadData()}
      />
    </Layout>
  );
};
