/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  CourseCloneRequest,
  CourseCreate,
  CourseDetail,
  CourseStatus,
  CourseSummary,
  GroupPartitionPreviewRequest,
  GroupSetResponse,
  GroupSetSaveRequest,
  JoinCodeResponse,
  LOCreate,
  LOResponse,
  LOUpdate,
  RosterImportResult,
  RosterItemResponse,
  RosterPageResponse,
  RosterPreviewResponse,
  RosterStudentCreate,
  SyllabusImportTemplateResponse,
  SyllabusUpdate,
} from "../types/course";
import { httpDownloadBlob, httpRequest } from "./httpClient";

export const courseService = {
  listCourses(params?: {
    role?: string;
    status?: string;
    q?: string;
  }): Promise<CourseSummary[]> {
    const query = new URLSearchParams();
    if (params?.role) query.set("role", params.role);
    if (params?.status) query.set("status", params.status);
    if (params?.q) query.set("q", params.q);
    const qs = query.toString();
    return httpRequest<CourseSummary[]>(`/courses${qs ? `?${qs}` : ""}`);
  },

  createCourse(payload: CourseCreate): Promise<CourseDetail> {
    return httpRequest<CourseDetail>("/courses", {
      method: "POST",
      body: payload,
    });
  },

  listTemplates(): Promise<CourseSummary[]> {
    return httpRequest<CourseSummary[]>("/courses/templates");
  },

  cloneCourse(payload: CourseCloneRequest): Promise<CourseDetail> {
    return httpRequest<CourseDetail>("/courses/clone", {
      method: "POST",
      body: payload,
    });
  },

  getCourseDetail(courseId: string): Promise<CourseDetail> {
    return httpRequest<CourseDetail>(`/courses/${courseId}`);
  },

  updateSyllabus(courseId: string, payload: SyllabusUpdate): Promise<CourseDetail> {
    return httpRequest<CourseDetail>(`/courses/${courseId}/syllabus`, {
      method: "PUT",
      body: payload,
    });
  },

  importSyllabusTemplate(
    courseId: string,
    templateId: string
  ): Promise<SyllabusImportTemplateResponse> {
    return httpRequest<SyllabusImportTemplateResponse>(
      `/courses/${courseId}/syllabus/import-template`,
      {
        method: "POST",
        body: { template_id: templateId },
      }
    );
  },

  transitionStatus(courseId: string, targetStatus: CourseStatus): Promise<CourseDetail> {
    return httpRequest<CourseDetail>(`/courses/${courseId}/status`, {
      method: "POST",
      body: { target_status: targetStatus },
    });
  },

  listLearningObjectives(courseId: string): Promise<LOResponse[]> {
    return httpRequest<LOResponse[]>(`/courses/${courseId}/learning-objectives`);
  },

  createLearningObjective(courseId: string, payload: LOCreate): Promise<LOResponse> {
    return httpRequest<LOResponse>(`/courses/${courseId}/learning-objectives`, {
      method: "POST",
      body: payload,
    });
  },

  updateLearningObjective(
    courseId: string,
    loId: string,
    payload: LOUpdate
  ): Promise<LOResponse> {
    return httpRequest<LOResponse>(
      `/courses/${courseId}/learning-objectives/${loId}`,
      {
        method: "PUT",
        body: payload,
      }
    );
  },

  deleteLearningObjective(courseId: string, loId: string): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/learning-objectives/${loId}`, {
      method: "DELETE",
    });
  },

  reorderLearningObjectives(courseId: string, orderedIds: string[]): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/learning-objectives/order`, {
      method: "PUT",
      body: { ordered_ids: orderedIds },
    });
  },

  getJoinCode(courseId: string): Promise<JoinCodeResponse> {
    return httpRequest<JoinCodeResponse>(`/courses/${courseId}/join-code`);
  },

  regenerateJoinCode(courseId: string): Promise<JoinCodeResponse> {
    return httpRequest<JoinCodeResponse>(
      `/courses/${courseId}/join-code/regenerate`,
      { method: "POST" }
    );
  },

  updateJoinCodeSettings(
    courseId: string,
    isEnrollmentOpen: boolean
  ): Promise<CourseDetail> {
    return httpRequest<CourseDetail>(`/courses/${courseId}/join-code/settings`, {
      method: "PUT",
      body: { is_enrollment_open: isEnrollmentOpen },
    });
  },

  joinByCode(joinCode: string): Promise<CourseSummary> {
    return httpRequest<CourseSummary>("/courses/join", {
      method: "POST",
      body: { join_code: joinCode },
    });
  },

  listRoster(
    courseId: string,
    params?: { q?: string; page?: number; pageSize?: number }
  ): Promise<RosterPageResponse> {
    const query = new URLSearchParams();
    if (params?.q) query.set("q", params.q);
    if (params?.page) query.set("page", String(params.page));
    if (params?.pageSize) query.set("page_size", String(params.pageSize));
    const qs = query.toString();
    return httpRequest<RosterPageResponse>(
      `/courses/${courseId}/roster${qs ? `?${qs}` : ""}`
    );
  },

  addSingleStudent(
    courseId: string,
    payload: RosterStudentCreate
  ): Promise<RosterItemResponse> {
    return httpRequest<RosterItemResponse>(`/courses/${courseId}/roster/students`, {
      method: "POST",
      body: payload,
    });
  },

  removeStudent(courseId: string, userId: string): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/roster/${userId}`, {
      method: "DELETE",
    });
  },

  downloadRosterTemplate(): Promise<void> {
    return httpDownloadBlob("/courses/roster/template", "adlas-roster-template.xlsx");
  },

  previewRosterUpload(courseId: string, file: File): Promise<RosterPreviewResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return httpRequest<RosterPreviewResponse>(`/courses/${courseId}/roster/preview`, {
      method: "POST",
      formData,
    });
  },

  confirmRosterUpload(
    courseId: string,
    file: File,
    sendNotification: boolean
  ): Promise<RosterImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("send_notification", String(sendNotification));
    return httpRequest<RosterImportResult>(`/courses/${courseId}/roster/confirm`, {
      method: "POST",
      formData,
    });
  },

  listGroups(courseId: string): Promise<GroupSetResponse[]> {
    return httpRequest<GroupSetResponse[]>(`/courses/${courseId}/groups`);
  },

  previewGroupPartition(
    courseId: string,
    payload: GroupPartitionPreviewRequest
  ): Promise<GroupSetResponse> {
    return httpRequest<GroupSetResponse>(
      `/courses/${courseId}/groups/partition/preview`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  saveGroupSet(
    courseId: string,
    groupSetName: string,
    payload: GroupSetSaveRequest
  ): Promise<GroupSetResponse> {
    return httpRequest<GroupSetResponse>(
      `/courses/${courseId}/groups/sets/${encodeURIComponent(groupSetName)}`,
      {
        method: "PUT",
        body: payload,
      }
    );
  },

  studentJoinGroup(courseId: string, groupId: string): Promise<void> {
    return httpRequest<void>(`/courses/${courseId}/groups/${groupId}/join`, {
      method: "POST",
    });
  },

  exportRosterXlsx(courseId: string, filename = "danh-sach-lop.xlsx"): Promise<void> {
    return httpDownloadBlob(`/courses/${courseId}/enrollments/export-roster`, filename);
  },
};
