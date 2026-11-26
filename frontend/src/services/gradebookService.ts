/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import { httpDownloadBlob, httpRequest } from "./httpClient";
import type {
  CellGradeDTO,
  ClassGradebookOverviewResponse,
  GradeAuditLogItem,
  GradebookLockPreviewResponse,
  GradebookLockResponse,
  GradebookStructureResponse,
  GradeColumnItem,
  GradeGroupInputPayload,
  GradeItemType,
  PostGradesResponse,
  PostGradesScope,
  RubricProposalResponse,
  SpeedGraderFilter,
  SpeedGraderSubmissionListResponse,
  SpeedGraderWorkspaceResponse,
  StudentMyGradesResponse,
  VersionDiffResponse,
} from "../types/gradebook";

export const gradebookService = {
  getStructure(courseId: string): Promise<GradebookStructureResponse> {
    return httpRequest<GradebookStructureResponse>(`/gradebook/courses/${courseId}/structure`);
  },

  saveStructure(
    courseId: string,
    groups: GradeGroupInputPayload[]
  ): Promise<GradebookStructureResponse> {
    return httpRequest<GradebookStructureResponse>(`/gradebook/courses/${courseId}/structure`, {
      method: "PUT",
      body: { groups },
    });
  },

  deleteGroup(courseId: string, groupId: string, confirmationText?: string): Promise<void> {
    return httpRequest<void>(`/gradebook/courses/${courseId}/groups/${groupId}`, {
      method: "DELETE",
      body: { confirmation_text: confirmationText ?? null },
    });
  },

  createColumn(
    courseId: string,
    payload: {
      group_id: string;
      title: string;
      item_type: GradeItemType;
      max_points: number;
      is_muted?: boolean;
    }
  ): Promise<GradeColumnItem> {
    return httpRequest<GradeColumnItem>(`/gradebook/courses/${courseId}/columns`, {
      method: "POST",
      body: payload,
    });
  },

  syncCourseItems(courseId: string): Promise<{ synced_assignments: number }> {
    return httpRequest<{ synced_assignments: number }>(
      `/gradebook/courses/${courseId}/sync-items`,
      { method: "POST" }
    );
  },

  getClassOverview(courseId: string): Promise<ClassGradebookOverviewResponse> {
    return httpRequest<ClassGradebookOverviewResponse>(`/gradebook/courses/${courseId}/overview`);
  },

  getStudentMyGrades(courseId: string): Promise<StudentMyGradesResponse> {
    return httpRequest<StudentMyGradesResponse>(`/gradebook/courses/${courseId}/my-grades`);
  },

  upsertManualGrade(
    courseId: string,
    columnId: string,
    payload: {
      user_id: string;
      official_score: number;
      instructor_feedback?: string;
      reason?: string;
    }
  ): Promise<CellGradeDTO> {
    return httpRequest<CellGradeDTO>(
      `/gradebook/courses/${courseId}/columns/${columnId}/grades`,
      { method: "PUT", body: payload }
    );
  },

  postColumnGrades(
    courseId: string,
    columnId: string,
    scope: PostGradesScope,
    sendNotification: boolean
  ): Promise<PostGradesResponse> {
    return httpRequest<PostGradesResponse>(
      `/gradebook/courses/${courseId}/columns/${columnId}/post-grades`,
      { method: "POST", body: { scope, send_notification: sendNotification } }
    );
  },

  muteColumnGrades(courseId: string, columnId: string): Promise<PostGradesResponse> {
    return httpRequest<PostGradesResponse>(
      `/gradebook/courses/${courseId}/columns/${columnId}/mute`,
      { method: "POST" }
    );
  },

  getLockPreview(courseId: string): Promise<GradebookLockPreviewResponse> {
    return httpRequest<GradebookLockPreviewResponse>(`/gradebook/courses/${courseId}/lock-preview`);
  },

  lockCourseGradebook(
    courseId: string,
    confirmationText: string
  ): Promise<GradebookLockResponse> {
    return httpRequest<GradebookLockResponse>(`/gradebook/courses/${courseId}/lock`, {
      method: "POST",
      body: { confirmation_text: confirmationText },
    });
  },

  emergencyUnlockGradebook(
    courseId: string,
    decisionCode: string,
    reason: string
  ): Promise<GradebookLockResponse> {
    return httpRequest<GradebookLockResponse>(`/gradebook/courses/${courseId}/emergency-unlock`, {
      method: "POST",
      body: { decision_code: decisionCode, reason },
    });
  },

  listAuditLogs(courseId: string): Promise<GradeAuditLogItem[]> {
    return httpRequest<GradeAuditLogItem[]>(`/gradebook/courses/${courseId}/audit-logs`);
  },

  listSpeedGraderSubmissions(
    assignmentId: string,
    filterMode: SpeedGraderFilter = "ALL"
  ): Promise<SpeedGraderSubmissionListResponse> {
    return httpRequest<SpeedGraderSubmissionListResponse>(
      `/gradebook/assignments/${assignmentId}/speedgrader/submissions?filter_mode=${filterMode}`
    );
  },

  getSpeedGraderWorkspace(submissionId: string): Promise<SpeedGraderWorkspaceResponse> {
    return httpRequest<SpeedGraderWorkspaceResponse>(
      `/gradebook/speedgrader/submissions/${submissionId}`
    );
  },

  generateAiRubricProposal(submissionId: string): Promise<RubricProposalResponse> {
    return httpRequest<RubricProposalResponse>(
      `/gradebook/speedgrader/submissions/${submissionId}/ai-propose`,
      { method: "POST" }
    );
  },

  saveSpeedGraderGrade(
    submissionId: string,
    payload: {
      official_score: number;
      rubric_scores: Record<string, { points: number; label?: string; lo_id?: string | null }>;
      instructor_feedback?: string;
      voice_feedback_url?: string | null;
      override_reason?: string;
    }
  ): Promise<SpeedGraderWorkspaceResponse> {
    return httpRequest<SpeedGraderWorkspaceResponse>(
      `/gradebook/speedgrader/submissions/${submissionId}/grade`,
      { method: "POST", body: payload }
    );
  },

  saveSpeedGraderDraft(
    submissionId: string,
    payload: {
      instructor_feedback?: string;
      rubric_scores?: Record<string, { points: number; label?: string; lo_id?: string | null }>;
    }
  ): Promise<{ status: string; saved_at: string }> {
    return httpRequest<{ status: string; saved_at: string }>(
      `/gradebook/speedgrader/submissions/${submissionId}/draft`,
      { method: "PATCH", body: payload }
    );
  },

  getSubmissionPreview(
    submissionId: string
  ): Promise<{ submission_id: string; file_url: string; preview_text: string }> {
    return httpRequest<{ submission_id: string; file_url: string; preview_text: string }>(
      `/gradebook/speedgrader/submissions/${submissionId}/preview`
    );
  },

  downloadSubmissionFile(submissionId: string, filename: string): Promise<void> {
    return httpDownloadBlob(
      `/gradebook/speedgrader/submissions/${submissionId}/download`,
      filename
    );
  },

  getVersionsDiff(submissionId: string, compareToId?: string): Promise<VersionDiffResponse> {
    const query = compareToId ? `?compare_to=${compareToId}` : "";
    return httpRequest<VersionDiffResponse>(
      `/gradebook/speedgrader/submissions/${submissionId}/diff${query}`
    );
  },

  uploadVoiceFeedback(
    blob: Blob,
    filename = "voice-feedback.webm"
  ): Promise<{ voice_feedback_url: string; storage_uri: string; storage_backend: string }> {
    const formData = new FormData();
    formData.append("file", blob, filename);
    return httpRequest<{
      voice_feedback_url: string;
      storage_uri: string;
      storage_backend: string;
    }>("/gradebook/voice-feedback/upload", {
      method: "POST",
      formData,
    });
  },
};
