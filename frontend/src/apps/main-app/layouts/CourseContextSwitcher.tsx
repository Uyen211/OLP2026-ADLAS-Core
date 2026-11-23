/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Check, ChevronDown } from "lucide-react";
import { useAuthStore } from "../../../stores/authStore";
import { useCourseContextStore } from "../../../stores/courseContextStore";
import type { ContextualRole } from "../../../types/course";
import { RoleBadge } from "../components/RoleBadge";

export const CourseContextSwitcher: React.FC = () => {
  const navigate = useNavigate();
  const me = useAuthStore((s) => s.me);
  const { activeCourseId, activeCourseName, activeRole, setActiveCourse } =
    useCourseContextStore();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const courseRoles = me?.course_roles ?? [];

  useEffect(() => {
    const onOutsideClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onOutsideClick);
    return () => document.removeEventListener("mousedown", onOutsideClick);
  }, []);

  if (courseRoles.length === 0) return null;

  const activeEntry = courseRoles.find((c) => c.course_id === activeCourseId);
  const displayLabel =
    activeCourseName ||
    activeEntry?.course_name ||
    activeEntry?.course_code ||
    "Chuyển môn học";

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex max-w-[260px] items-center gap-2 rounded-full border border-mm-border bg-mm-bg px-3.5 py-1.5 font-mm-ui text-sm text-mm-heading transition-colors hover:bg-mm-divider/60"
      >
        <BookOpen className="h-4 w-4 shrink-0 text-mm-blue-primary" />
        <span className="truncate font-medium">{displayLabel}</span>
        {activeRole && <RoleBadge role={activeRole} className="hidden sm:inline-flex" />}
        <ChevronDown className="h-4 w-4 shrink-0 text-mm-text-muted" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-30 mt-2 w-80 overflow-hidden rounded-mm-card border border-mm-border bg-mm-bg p-2 shadow-mm-elevated">
          <div className="px-3 py-2 font-mm-ui text-xs font-medium text-mm-text-muted">
            Ngữ cảnh môn học (BR-01)
          </div>
          <div className="max-h-72 space-y-1 overflow-y-auto">
            {courseRoles.map((entry) => {
              const isSelected = entry.course_id === activeCourseId;
              return (
                <button
                  key={entry.course_id}
                  type="button"
                  onClick={() => {
                    setActiveCourse({
                      courseId: entry.course_id,
                      role: entry.role as ContextualRole,
                      courseName: entry.course_name ?? entry.course_code ?? null,
                    });
                    setOpen(false);
                    navigate(`/courses/${entry.course_id}`);
                  }}
                  className="flex w-full items-center justify-between gap-2 rounded-mm-panel px-3 py-2 text-left transition-colors hover:bg-mm-divider/70"
                >
                  <div className="min-w-0">
                    <p className="truncate font-mm-ui text-sm font-medium text-mm-heading">
                      {entry.course_name || entry.course_code || "Môn học"}
                    </p>
                    {entry.course_code && (
                      <p className="font-mm-data text-xs text-mm-text-muted">
                        {entry.course_code}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <RoleBadge role={entry.role} />
                    {isSelected && <Check className="h-4 w-4 text-mm-blue-primary" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
