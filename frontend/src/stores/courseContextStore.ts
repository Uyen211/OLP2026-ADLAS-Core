/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import { create } from "zustand";
import type { ContextualRole } from "../types/course";

interface CourseContextState {
  activeCourseId: string | null;
  activeRole: ContextualRole | null;
  activeCourseName: string | null;
  setActiveCourse: (params: {
    courseId: string;
    role: ContextualRole | null;
    courseName?: string | null;
  }) => void;
  clearActiveCourse: () => void;
}

export const useCourseContextStore = create<CourseContextState>((set) => ({
  activeCourseId: null,
  activeRole: null,
  activeCourseName: null,
  setActiveCourse: ({ courseId, role, courseName }) =>
    set({
      activeCourseId: courseId,
      activeRole: role,
      activeCourseName: courseName ?? null,
    }),
  clearActiveCourse: () =>
    set({
      activeCourseId: null,
      activeRole: null,
      activeCourseName: null,
    }),
}));
