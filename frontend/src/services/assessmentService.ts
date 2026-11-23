/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  AssignmentDetail,
  PresignedUploadUrlRequest,
  PresignedUploadUrlResponse,
  Submission,
  SubmissionCreateRequest,
  VivaAnswerSubmitRequest,
  VivaAnswerSubmitResponse,
  VivaSecurityViolationRequest,
  VivaStartResponse,
} from "../types/assessment";
import { httpRequest } from "./httpClient";

export const assessmentService = {
  /**
   * Lấy thông tin chi tiết bài tập, lịch hạn chót và lịch sử bài nộp của sinh viên
   */
  getAssignmentDetail(assignmentId: string): Promise<AssignmentDetail> {
    return httpRequest<AssignmentDetail>(`/assessments/assignments/${assignmentId}`);
  },

  /**
   * Nộp bài tập kèm bản cam kết trung thực và bảng giải trình sử dụng AI (AI Disclosure)
   */
  createSubmission(
    assignmentId: string,
    payload: SubmissionCreateRequest
  ): Promise<Submission> {
    return httpRequest<Submission>(`/assessments/assignments/${assignmentId}/submissions`, {
      method: "POST",
      body: payload,
    });
  },

  /**
   * Bắt đầu hoặc tiếp tục phiên vấn đáp Viva trong phòng thi cô lập
   */
  startVivaSession(submissionId: string): Promise<VivaStartResponse> {
    return httpRequest<VivaStartResponse>(`/assessments/submissions/${submissionId}/viva/start`, {
      method: "POST",
    });
  },

  /**
   * Gửi câu trả lời cho câu hỏi Viva hiện tại
   */
  submitVivaAnswer(
    submissionId: string,
    payload: VivaAnswerSubmitRequest
  ): Promise<VivaAnswerSubmitResponse> {
    return httpRequest<VivaAnswerSubmitResponse>(
      `/assessments/submissions/${submissionId}/viva/answers`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  /**
   * Ghi nhận vi phạm an ninh phòng thi (Paste attempt, Window blur ra ngoài)
   */
  recordSecurityViolation(
    submissionId: string,
    payload: VivaSecurityViolationRequest
  ): Promise<{ recorded: boolean; violation_type: string }> {
    return httpRequest<{ recorded: boolean; violation_type: string }>(
      `/assessments/submissions/${submissionId}/viva/violations`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  /**
   * Lấy presigned URL để tải tệp trực tiếp lên MinIO/S3
   */
  getPresignedUploadUrl(
    payload: PresignedUploadUrlRequest
  ): Promise<PresignedUploadUrlResponse> {
    return httpRequest<PresignedUploadUrlResponse>("/assessments/presigned-upload-url", {
      method: "POST",
      body: payload,
    });
  },

  /**
   * Tải tệp bài nộp trực tiếp lên máy chủ để trích xuất nội dung văn bản / mã nguồn
   */
  async uploadFile(file: File): Promise<{ file_url: string; file_name: string }> {
    const formData = new FormData();
    formData.append("file", file);
    const token =
      localStorage.getItem("adlas_access_token") ||
      sessionStorage.getItem("adlas_access_token") ||
      "";
    const response = await fetch("/api/v1/assessments/upload", {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!response.ok) {
      throw new Error("Tải tệp bài nộp lên máy chủ thất bại.");
    }
    return response.json();
  },
};
