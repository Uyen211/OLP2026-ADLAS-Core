/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  BookOpen,
  Calendar,
  Copy,
  KeyRound,
  Plus,
  Search,
  Target,
  Users,
} from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import { useAuthStore } from "../../../../stores/authStore";
import { useCourseContextStore } from "../../../../stores/courseContextStore";
import type { CourseStatus, CourseSummary } from "../../../../types/course";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { PillFilter, type PillFilterOption } from "../../components/PillFilter";
import { RoleBadge } from "../../components/RoleBadge";
import { showToast } from "../../components/Toast";
import { StudentLayout } from "../../layouts/StudentLayout";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { CloneTemplateModal } from "./CloneTemplateModal";
import { CreateCourseModal } from "./CreateCourseModal";
import { JoinCourseModal } from "./JoinCourseModal";
import { JoinByCodeBanner } from "../../../../features/tv3/course/components/JoinByCodeBanner";

type FilterValue = "all" | "teaching" | "learning" | "template";

const STATUS_LABELS: Record<CourseStatus, { label: string; className: string }> = {
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
    label: "Đã lưu trữ",
    className: "bg-mm-divider text-mm-text-muted",
  },
};

export const CourseListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const me = useAuthStore((s) => s.me);
  const setActiveCourse = useCourseContextStore((s) => s.setActiveCourse);

  const initialFilter = (searchParams.get("filter") as FilterValue) || "all";
  const [filter, setFilter] = useState<FilterValue>(
    ["all", "teaching", "learning", "template"].includes(initialFilter)
      ? initialFilter
      : "all"
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);

  const canCreateCourse = useMemo(() => {
    if (!me) return false;
    if (me.system_role === "ADMIN") return true;
    return me.course_roles.some((r) => r.role === "INSTRUCTOR");
  }, [me]);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await courseService.listCourses();
      setCourses(data);
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải danh sách môn học."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  const filteredCourses = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return courses.filter((course) => {
      if (filter === "teaching" && (course.my_role !== "INSTRUCTOR" || course.is_template)) {
        return false;
      }
      if (filter === "learning" && course.my_role !== "STUDENT") {
        return false;
      }
      if (filter === "template" && !course.is_template) {
        return false;
      }
      if (q) {
        const hay = `${course.course_code} ${course.section_code} ${course.name} ${course.semester}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [courses, filter, searchQuery]);

  const filterOptions: PillFilterOption<FilterValue>[] = useMemo(() => {
    const teachingCount = courses.filter(
      (c) => c.my_role === "INSTRUCTOR" && !c.is_template
    ).length;
    const learningCount = courses.filter((c) => c.my_role === "STUDENT").length;
    const templateCount = courses.filter((c) => c.is_template).length;
    return [
      { value: "all", label: "Tất cả", count: courses.length },
      { value: "teaching", label: "Đang giảng dạy", count: teachingCount },
      { value: "learning", label: "Đang học", count: learningCount },
      { value: "template", label: "Môn mẫu", count: templateCount },
    ];
  }, [courses]);

  const handleOpenCourse = (course: CourseSummary) => {
    setActiveCourse({
      courseId: course.id,
      role: course.my_role ?? null,
      courseName: course.name,
    });
    navigate(`/courses/${course.id}`);
  };

  const Layout = canCreateCourse ? TeacherLayout : StudentLayout;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="font-mm-display text-[31px] font-semibold tracking-tight text-mm-heading">
              Môn học của tôi
            </h1>
            <p className="mt-1 font-mm-ui text-sm text-mm-text-secondary">
              Quản lý đề cương, chuẩn đầu ra và danh sách lớp học phần của bạn
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <MmButton variant="secondary" onClick={() => setJoinOpen(true)}>
              <KeyRound className="h-4 w-4" />
              <span>Nhập mã vào lớp</span>
            </MmButton>

            {canCreateCourse && (
              <>
                <MmButton variant="secondary" onClick={() => setCloneOpen(true)}>
                  <Copy className="h-4 w-4" />
                  <span>Nhân bản môn mẫu</span>
                </MmButton>
                <MmButton variant="brand" onClick={() => setCreateOpen(true)}>
                  <Plus className="h-4 w-4" />
                  <span>Tạo môn học mới</span>
                </MmButton>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-col justify-between gap-4 border-b border-mm-divider pb-4 md:flex-row md:items-center">
          <PillFilter
            options={filterOptions}
            value={filter}
            onChange={(next) => {
              setFilter(next);
              setSearchParams(next === "all" ? {} : { filter: next });
            }}
          />

          <div className="relative w-full md:w-72">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mm-text-muted" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo tên môn hoặc mã môn..."
              className="w-full rounded-full border border-mm-border bg-mm-bg py-2 pl-10 pr-4 font-mm-ui text-sm text-mm-text placeholder:text-mm-text-muted focus:border-mm-blue-hover focus:outline-none focus:ring-2 focus:ring-mm-blue-hover/20"
            />
          </div>
        </div>

        <JoinByCodeBanner onSuccess={() => loadCourses()} className="mb-6" />

        {loading ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[1, 2, 3, 4].map((skeleton) => (
              <div
                key={skeleton}
                className="h-64 animate-pulse rounded-mm-card border border-mm-border bg-mm-divider/50"
              />
            ))}
          </div>
        ) : filteredCourses.length === 0 ? (
          <MmCard variant="standard" className="py-14 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-mm-blue-light/40 text-mm-blue-primary">
              <BookOpen className="h-7 w-7" />
            </div>
            <h2 className="font-mm-display text-xl font-medium text-mm-heading">
              Chưa có môn học phù hợp
            </h2>
            <p className="mx-auto mt-2 max-w-md font-mm-ui text-sm text-mm-text-secondary">
              Bạn có thể tham gia lớp học mới bằng mã 6 ký tự từ giảng viên
              {canCreateCourse ? " hoặc tạo môn học mới để bắt đầu giảng dạy." : "."}
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <MmButton variant="secondary" onClick={() => setJoinOpen(true)}>
                <KeyRound className="h-4 w-4" />
                <span>Nhập mã vào lớp</span>
              </MmButton>
              {canCreateCourse && (
                <MmButton variant="brand" onClick={() => setCreateOpen(true)}>
                  <Plus className="h-4 w-4" />
                  <span>Tạo môn học mới</span>
                </MmButton>
              )}
            </div>
          </MmCard>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredCourses.map((course) => {
              const statusMeta = STATUS_LABELS[course.status];
              return (
                <MmCard
                  key={course.id}
                  variant="featured"
                  radius="card"
                  padding="none"
                  interactive
                  onClick={() => handleOpenCourse(course)}
                  className="flex flex-col overflow-hidden"
                >
                  <div className="relative h-24 bg-gradient-to-r from-[#1456f0] to-[#3daeff] p-4">
                    <div className="flex items-start justify-between gap-2">
                      <span className="rounded-mm-tag bg-white/20 px-2.5 py-0.5 font-mm-data text-[13px] font-medium text-white backdrop-blur-sm">
                        {course.course_code} · {course.section_code}
                      </span>
                      {course.is_template && (
                        <span className="rounded-full bg-mm-dark/70 px-2.5 py-0.5 font-mm-ui text-[11px] font-medium text-white">
                          Môn mẫu
                        </span>
                      )}
                    </div>
                    <p className="mt-3 font-mm-data text-xs text-white/90">
                      {course.semester} · {course.credits} tín chỉ
                    </p>
                  </div>

                  <div className="flex flex-1 flex-col justify-between p-5">
                    <div>
                      <div className="mb-2.5 flex flex-wrap items-center gap-2">
                        <RoleBadge role={course.my_role} />
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mm-ui text-xs font-medium ${statusMeta.className}`}
                        >
                          {statusMeta.label}
                        </span>
                      </div>
                      <h2 className="line-clamp-2 font-mm-display text-[20px] font-medium leading-snug text-mm-heading">
                        {course.name}
                      </h2>
                    </div>

                    <div className="mt-5 flex items-center justify-between border-t border-mm-divider pt-3 font-mm-data text-xs text-mm-text-secondary">
                      <span className="inline-flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5 text-mm-text-muted" />
                        {course.student_count} SV
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Target className="h-3.5 w-3.5 text-mm-text-muted" />
                        {course.lo_count} LO
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5 text-mm-text-muted" />
                        {course.start_date}
                      </span>
                    </div>
                  </div>
                </MmCard>
              );
            })}
          </div>
        )}
      </div>

      <CreateCourseModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(created) => {
          setCreateOpen(false);
          navigate(`/courses/${created.id}`);
        }}
      />

      <CloneTemplateModal
        open={cloneOpen}
        mode="create-course"
        onClose={() => setCloneOpen(false)}
        onClonedCourse={(created) => {
          navigate(`/courses/${created.id}`);
        }}
      />

      <JoinCourseModal
        open={joinOpen}
        onClose={() => setJoinOpen(false)}
        onJoined={() => {
          void loadCourses();
        }}
      />
    </Layout>
  );
};
