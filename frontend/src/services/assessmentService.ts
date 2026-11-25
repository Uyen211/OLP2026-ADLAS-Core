/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  AssignmentDetail,
  AssignmentSummaryItem,
  PresignedUploadUrlRequest,
  PresignedUploadUrlResponse,
  Submission,
  SubmissionCreateRequest,
  SubmissionReviewDetailResponse,
  SubmissionReviewSummaryItem,
  VivaAnswerSubmitRequest,
  VivaAnswerSubmitResponse,
  VivaSecurityViolationRequest,
  VivaStartResponse,
  VivaTimeoutRequest,
} from "../types/assessment";
import { httpRequest } from "./httpClient";

export const assessmentService = {
  /**
   * Lấy danh sách bài tập của một môn học
   */
  listCourseAssignments(courseId: string): Promise<AssignmentSummaryItem[]> {
    return httpRequest<AssignmentSummaryItem[]>(`/assessments/courses/${courseId}/assignments`);
  },

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
   * Tự động niêm phong phiên vấn đáp khi hết giờ đếm ngược
   */
  timeoutVivaSession(
    submissionId: string,
    payload: VivaTimeoutRequest = {}
  ): Promise<VivaAnswerSubmitResponse> {
    return httpRequest<VivaAnswerSubmitResponse>(
      `/assessments/submissions/${submissionId}/viva/timeout`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  /**
   * Tải tệp bài nộp trực tiếp lên máy chủ để trích xuất nội dung văn bản / mã nguồn
   */
  uploadFile(file: File): Promise<{ file_url: string; file_name: string }> {
    const formData = new FormData();
    formData.append("file", file);
    return httpRequest<{ file_url: string; file_name: string }>("/assessments/upload", {
      method: "POST",
      formData,
    });
  },

  /**
   * [Giảng viên] Lấy toàn bộ danh sách bài nộp của sinh viên cho một bài tập
   */
  listAssignmentSubmissions(assignmentId: string): Promise<SubmissionReviewSummaryItem[]> {
    return httpRequest<SubmissionReviewSummaryItem[]>(
      `/assessments/assignments/${assignmentId}/submissions`
    );
  },

  /**
   * [Giảng viên] Tải chi tiết tóm tắt AI, câu hỏi Viva, câu trả lời và nhật ký vi phạm
   */
  getSubmissionReview(submissionId: string): Promise<SubmissionReviewDetailResponse> {
    return httpRequest<SubmissionReviewDetailResponse>(
      `/assessments/submissions/${submissionId}/review`
    );
  },
};
