/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Check,
  Copy,
  RefreshCw,
  Search,
  Shuffle,
  Trash2,
  Upload,
  UserPlus,
  Users,
} from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import type {
  CourseDetail,
  GroupSetResponse,
  RosterItemResponse,
} from "../../../../types/course";
import { ConfirmModal } from "../../components/ConfirmModal";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { showToast } from "../../components/Toast";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { AddStudentModal } from "./AddStudentModal";
import { GroupPartitionModal } from "./GroupPartitionModal";
import { RosterImportModal } from "./RosterImportModal";
import { RosterExportButton } from "../../../../features/tv3/course/components/RosterExportButton";

export interface StudentRosterPageProps {
  courseIdProp?: string;
  courseProp?: CourseDetail | null;
  embedded?: boolean;
  onCourseUpdated?: (course: CourseDetail) => void;
}

export const StudentRosterPage: React.FC<StudentRosterPageProps> = ({
  courseIdProp,
  courseProp,
  embedded = false,
  onCourseUpdated,
}) => {
  const params = useParams<{ courseId: string }>();
  const courseId = courseIdProp ?? params.courseId ?? "";
  const me = useAuthStore((s) => s.me);

  const [course, setCourse] = useState<CourseDetail | null>(courseProp ?? null);
  const [joinCode, setJoinCode] = useState<string | null>(courseProp?.join_code ?? null);
  const [enrollmentOpen, setEnrollmentOpen] = useState<boolean>(
    courseProp?.is_enrollment_open ?? false
  );
  const [copied, setCopied] = useState(false);

  const [rosterItems, setRosterItems] = useState<RosterItemResponse[]>([]);
  const [totalStudents, setTotalStudents] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingRoster, setLoadingRoster] = useState(false);

  const [groupSets, setGroupSets] = useState<GroupSetResponse[]>([]);
  const [loadingGroups, setLoadingGroups] = useState(false);

  const [addStudentOpen, setAddStudentOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [partitionOpen, setPartitionOpen] = useState(false);

  const [confirmRegenerate, setConfirmRegenerate] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [togglingEnrollment, setTogglingEnrollment] = useState(false);

  const [removingStudent, setRemovingStudent] = useState<RosterItemResponse | null>(null);
  const [removingLoading, setRemovingLoading] = useState(false);
  const [joiningGroupId, setJoiningGroupId] = useState<string | null>(null);

  const isInstructor =
    course?.my_role === "INSTRUCTOR" || me?.system_role === "ADMIN";
  const isReadOnly = course?.status === "ARCHIVED" || Boolean(course?.is_template);

  useEffect(() => {
    if (courseProp) {
      setCourse(courseProp);
      setJoinCode(courseProp.join_code ?? null);
      setEnrollmentOpen(courseProp.is_enrollment_open);
    }
  }, [courseProp]);

  const loadCourseIfNeeded = useCallback(async () => {
    if (courseProp || !courseId) return;
    try {
      const detail = await courseService.getCourseDetail(courseId);
      setCourse(detail);
      setJoinCode(detail.join_code ?? null);
      setEnrollmentOpen(detail.is_enrollment_open);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải thông tin lớp học."
      );
    }
  }, [courseId, courseProp]);

  const loadRoster = useCallback(async () => {
    if (!courseId || !isInstructor) return;
    setLoadingRoster(true);
    try {
      const page = await courseService.listRoster(courseId, {
        q: searchQuery.trim() || undefined,
        page: 1,
        pageSize: 200,
      });
      setRosterItems(page.items);
      setTotalStudents(page.total);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải danh sách sinh viên."
      );
    } finally {
      setLoadingRoster(false);
    }
  }, [courseId, isInstructor, searchQuery]);

  const loadGroups = useCallback(async () => {
    if (!courseId) return;
    setLoadingGroups(true);
    try {
      const sets = await courseService.listGroups(courseId);
      setGroupSets(sets);
    } catch {
      // Ignore if student has no groups yet
    } finally {
      setLoadingGroups(false);
    }
  }, [courseId]);

  useEffect(() => {
    void loadCourseIfNeeded();
  }, [loadCourseIfNeeded]);

  useEffect(() => {
    void loadRoster();
  }, [loadRoster]);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  const handleCopyCode = async () => {
    if (!joinCode) return;
    try {
      await navigator.clipboard.writeText(joinCode);
      setCopied(true);
      showToast("success", `Đã sao chép mã lớp ${joinCode}!`);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast("warning", "Trình duyệt không cho phép sao chép tự động.");
    }
  };

  const handleRegenerateCode = async () => {
    setRegenerating(true);
    try {
      const res = await courseService.regenerateJoinCode(courseId);
      setJoinCode(res.join_code ?? null);
      setEnrollmentOpen(res.is_enrollment_open);
      showToast("success", `Đã cấp mã vào lớp mới: ${res.join_code ?? ""}`);
      setConfirmRegenerate(false);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể cấp mã vào lớp mới."
      );
    } finally {
      setRegenerating(false);
    }
  };

  const handleToggleEnrollment = async () => {
    setTogglingEnrollment(true);
    try {
      const updated = await courseService.updateJoinCodeSettings(
        courseId,
        !enrollmentOpen
      );
      setCourse(updated);
      setEnrollmentOpen(updated.is_enrollment_open);
      onCourseUpdated?.(updated);
      showToast(
        "success",
        updated.is_enrollment_open
          ? "Đã bật cho phép sinh viên tự vào lớp bằng mã."
          : "Đã tắt tự vào lớp bằng mã."
      );
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError
          ? err.message
          : "Không thể thay đổi trạng thái ghi danh."
      );
    } finally {
      setTogglingEnrollment(false);
    }
  };

  const handleRemoveStudent = async () => {
    if (!removingStudent) return;
    setRemovingLoading(true);
    try {
      await courseService.removeStudent(courseId, removingStudent.user_id);
      showToast("success", `Đã xóa sinh viên ${removingStudent.full_name} khỏi lớp.`);
      setRemovingStudent(null);
      void loadRoster();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể xóa sinh viên khỏi lớp."
      );
    } finally {
      setRemovingLoading(false);
    }
  };

  const handleStudentJoinGroup = async (groupId: string) => {
    setJoiningGroupId(groupId);
    try {
      await courseService.studentJoinGroup(courseId, groupId);
      showToast("success", "Bạn đã tham gia nhóm thành công!");
      void loadGroups();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tham gia nhóm này."
      );
    } finally {
      setJoiningGroupId(null);
    }
  };

  const content = (
    <div className="space-y-6">
      {isInstructor && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <MmCard
            variant="featured"
            radius="card-lg"
            padding="lg"
            className="lg:col-span-7"
          >
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <p className="font-mm-ui text-xs font-medium uppercase tracking-wider text-mm-text-muted">
                  Mã vào lớp (Join Code)
                </p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="font-mm-mono text-[40px] font-medium leading-none tracking-[0.2em] text-mm-heading">
                    {joinCode || "------"}
                  </span>
                  {joinCode && (
                    <MmButton
                      variant="secondary"
                      size="sm"
                      onClick={handleCopyCode}
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-mm-success" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                      <span>{copied ? "Đã chép" : "Sao chép"}</span>
                    </MmButton>
                  )}
                </div>
              </div>

              {!isReadOnly && (
                <MmButton
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmRegenerate(true)}
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Cấp mã mới</span>
                </MmButton>
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-mm-divider pt-4">
              <span className="font-mm-ui text-sm text-mm-text-secondary">
                Cho phép sinh viên tự vào lớp bằng mã
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={enrollmentOpen}
                disabled={isReadOnly || togglingEnrollment}
                onClick={handleToggleEnrollment}
                className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  enrollmentOpen ? "bg-mm-blue-hover" : "bg-mm-border"
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                    enrollmentOpen ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </MmCard>

          <MmCard
            variant="standard"
            radius="card-lg"
            padding="lg"
            className="flex flex-col justify-between lg:col-span-5"
          >
            <div>
              <h3 className="font-mm-mid text-lg font-medium text-mm-heading">
                Thao tác danh sách lớp
              </h3>
              <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
                Tổng số:{" "}
                <span className="font-mm-data font-medium text-mm-heading">
                  {totalStudents} sinh viên
                </span>
              </p>
            </div>

            <div className="mt-5 flex flex-wrap gap-2.5">
              <MmButton
                variant="brand"
                disabled={isReadOnly}
                onClick={() => setImportOpen(true)}
              >
                <Upload className="h-4 w-4" />
                <span>Nhập Excel / CSV</span>
              </MmButton>
              <MmButton
                variant="secondary"
                disabled={isReadOnly}
                onClick={() => setAddStudentOpen(true)}
              >
                <UserPlus className="h-4 w-4" />
                <span>Thêm sinh viên lẻ</span>
              </MmButton>
              <RosterExportButton courseId={courseId} courseCode={course?.course_code} />
              <MmButton
                variant="secondary"
                disabled={isReadOnly || totalStudents === 0}
                onClick={() => setPartitionOpen(true)}
              >
                <Shuffle className="h-4 w-4" />
                <span>Phân nhóm</span>
              </MmButton>
            </div>
          </MmCard>
        </div>
      )}

      {isInstructor && (
        <MmCard variant="standard" radius="card" padding="none">
          <div className="flex flex-col justify-between gap-3 border-b border-mm-divider px-6 py-4 sm:flex-row sm:items-center">
            <div>
              <h3 className="font-mm-mid text-lg font-medium text-mm-heading">
                Danh sách sinh viên
              </h3>
              <p className="font-mm-data text-xs text-mm-text-muted">
                Tổng số: {totalStudents} sinh viên
              </p>
            </div>

            <div className="relative w-full sm:w-72">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mm-text-muted" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm theo họ tên hoặc MSSV..."
                className="w-full rounded-full border border-mm-border bg-mm-bg py-2 pl-10 pr-4 font-mm-ui text-sm text-mm-text placeholder:text-mm-text-muted focus:border-mm-blue-hover focus:outline-none focus:ring-2 focus:ring-mm-blue-hover/20"
              />
            </div>
          </div>

          {loadingRoster ? (
            <div className="p-8 text-center font-mm-ui text-sm text-mm-text-muted">
              Đang tải danh sách sinh viên...
            </div>
          ) : rosterItems.length === 0 ? (
            <div className="p-10 text-center">
              <Users className="mx-auto mb-3 h-8 w-8 text-mm-text-muted" />
              <p className="font-mm-ui text-sm text-mm-text-secondary">
                Chưa có sinh viên nào trong danh sách lớp.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-mm-divider bg-mm-divider/40 font-mm-ui text-xs font-medium text-mm-text-secondary">
                    <th className="px-6 py-3">STT</th>
                    <th className="px-6 py-3">MSSV</th>
                    <th className="px-6 py-3">Họ và tên</th>
                    <th className="px-6 py-3">Email</th>
                    <th className="px-6 py-3">Nhóm đồ án</th>
                    <th className="px-6 py-3">Trạng thái</th>
                    {!isReadOnly && <th className="px-6 py-3 text-right">Thao tác</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-mm-divider font-mm-ui text-sm">
                  {rosterItems.map((student, idx) => (
                    <tr key={student.user_id} className="hover:bg-mm-divider/20">
                      <td className="px-6 py-3.5 font-mm-data text-xs text-mm-text-muted">
                        {idx + 1}
                      </td>
                      <td className="px-6 py-3.5 font-mm-mono text-xs text-mm-heading">
                        {student.user_code || "—"}
                      </td>
                      <td className="px-6 py-3.5 font-medium text-mm-heading">
                        {student.full_name}
                      </td>
                      <td className="px-6 py-3.5 text-mm-text-secondary">
                        {student.email}
                      </td>
                      <td className="px-6 py-3.5">
                        {student.group_name ? (
                          <span className="inline-flex rounded-full bg-mm-blue-light/50 px-2.5 py-0.5 text-xs font-medium text-mm-blue-deep">
                            {student.group_name}
                          </span>
                        ) : (
                          <span className="text-xs text-mm-text-muted">Chưa xếp nhóm</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={
                            student.status === "ACTIVE"
                              ? "inline-flex rounded-full bg-mm-success-bg px-2.5 py-0.5 text-xs font-medium text-mm-success"
                              : student.status === "COMPLETED"
                                ? "inline-flex rounded-full bg-mm-blue-light/50 px-2.5 py-0.5 text-xs font-medium text-mm-blue-deep"
                                : "inline-flex rounded-full bg-mm-divider px-2.5 py-0.5 text-xs font-medium text-mm-text-muted"
                          }
                        >
                          {student.status === "ACTIVE"
                            ? "Đang học"
                            : student.status === "COMPLETED"
                              ? "Hoàn thành"
                              : "Đã rời lớp"}
                        </span>
                      </td>
                      {!isReadOnly && (
                        <td className="px-6 py-3.5 text-right">
                          <button
                            type="button"
                            aria-label={`Xóa ${student.full_name}`}
                            onClick={() => setRemovingStudent(student)}
                            className="inline-flex items-center gap-1 rounded-mm-btn px-2.5 py-1.5 text-xs font-medium text-mm-danger hover:bg-mm-danger-bg"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            <span>Xóa</span>
                          </button>
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

      <MmCard variant="standard" radius="card" padding="lg">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="font-mm-mid text-lg font-medium text-mm-heading">
              Danh sách nhóm học tập
            </h3>
            <p className="font-mm-ui text-xs text-mm-text-helper">
              Các bộ nhóm đã được thiết lập trong lớp học phần này
            </p>
          </div>
        </div>

        {loadingGroups ? (
          <p className="py-6 text-center font-mm-ui text-sm text-mm-text-muted">
            Đang tải danh sách nhóm...
          </p>
        ) : groupSets.length === 0 ? (
          <p className="py-6 text-center font-mm-ui text-sm text-mm-text-secondary">
            Chưa có bộ nhóm nào được tạo trong lớp học này.
          </p>
        ) : (
          <div className="space-y-6">
            {groupSets.map((set) => (
              <div key={set.group_set_name} className="space-y-3">
                <h4 className="font-mm-mid text-base font-medium text-mm-heading">
                  {set.group_set_name}
                </h4>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {set.groups.map((grp) => {
                    const isMember = grp.members.some((m) => m.user_id === me?.id);
                    return (
                      <div
                        key={grp.id ?? grp.name}
                        className="rounded-mm-panel border border-mm-border bg-mm-bg p-4"
                      >
                        <div className="mb-2.5 flex items-center justify-between border-b border-mm-divider pb-2">
                          <span className="font-mm-ui text-sm font-semibold text-mm-heading">
                            {grp.name}
                          </span>
                          <span className="rounded-full bg-mm-divider px-2.5 py-0.5 font-mm-data text-xs text-mm-text-secondary">
                            {grp.members.length} thành viên
                          </span>
                        </div>
                        {grp.members.length === 0 ? (
                          <p className="py-2 font-mm-ui text-xs text-mm-text-muted">
                            Chưa có thành viên
                          </p>
                        ) : (
                          <ul className="space-y-1.5">
                            {grp.members.map((m) => (
                              <li
                                key={m.user_id}
                                className="flex items-center justify-between font-mm-ui text-xs text-mm-text-secondary"
                              >
                                <span className="truncate font-medium text-mm-heading">
                                  {m.full_name}
                                </span>
                                <span className="font-mm-mono text-[11px] text-mm-text-muted">
                                  {m.user_code || ""}
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                        {!isInstructor && !isMember && grp.id && (
                          <MmButton
                            variant="secondary"
                            size="sm"
                            fullWidth
                            loading={joiningGroupId === grp.id}
                            onClick={() => grp.id && handleStudentJoinGroup(grp.id)}
                            className="mt-3"
                          >
                            Tham gia nhóm
                          </MmButton>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </MmCard>

      <AddStudentModal
        open={addStudentOpen}
        courseId={courseId}
        onClose={() => setAddStudentOpen(false)}
        onAdded={() => void loadRoster()}
      />

      <RosterImportModal
        open={importOpen}
        courseId={courseId}
        onClose={() => setImportOpen(false)}
        onImported={() => void loadRoster()}
      />

      <GroupPartitionModal
        open={partitionOpen}
        courseId={courseId}
        onClose={() => setPartitionOpen(false)}
        onSaved={() => {
          void loadGroups();
          void loadRoster();
        }}
      />

      <ConfirmModal
        open={confirmRegenerate}
        title="Cấp mã vào lớp mới?"
        description="Mã vào lớp cũ sẽ lập tức hết hiệu lực. Sinh viên chưa ghi danh sẽ cần sử dụng mã mới để tham gia lớp."
        confirmLabel="Cấp mã mới"
        danger={false}
        loading={regenerating}
        onConfirm={handleRegenerateCode}
        onCancel={() => setConfirmRegenerate(false)}
      />

      <ConfirmModal
        open={Boolean(removingStudent)}
        title="Xóa sinh viên khỏi lớp học?"
        description={`Bạn có chắc muốn xóa sinh viên ${removingStudent?.full_name ?? ""} khỏi danh sách lớp? Lịch sử học tập sẽ được giữ lại và có thể thêm lại sau.`}
        confirmLabel="Xóa khỏi lớp"
        danger
        loading={removingLoading}
        onConfirm={handleRemoveStudent}
        onCancel={() => setRemovingStudent(null)}
      />
    </div>
  );

  if (embedded) return content;

  return <TeacherLayout>{content}</TeacherLayout>;
};
