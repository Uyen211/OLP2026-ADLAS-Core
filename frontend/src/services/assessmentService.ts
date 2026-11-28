/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  AssignmentAuthoringResponse,
  AssignmentCreateRequest,
  AssignmentDeleteResponse,
  AssignmentDetail,
  AssignmentSummaryItem,
  AssignmentUpdateRequest,
  GroupCreateRequest,
  MilestoneCreateRequest,
  MilestoneResponse,
  PeerReviewResponse,
  PeerReviewSubmitRequest,
  PeerReviewSummaryResponse,
  PledgeSignRequest,
  PledgeSignResponse,
  PledgeStatusResponse,
  PresignedUploadUrlRequest,
  PresignedUploadUrlResponse,
  RubricResponse,
  RubricSaveRequest,
  StudentGroupResponse,
  Submission,
  SubmissionCreateRequest,
  SubmissionReviewDetailResponse,
  SubmissionReviewSummaryItem,
  TopicCreateRequest,
  TopicResponse,
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

  /**
   * [Giảng viên] Tạo mới bài tập / đồ án (Bản nháp hoặc Xuất bản ngay)
   */
  createAssignment(
    courseId: string,
    payload: AssignmentCreateRequest
  ): Promise<AssignmentAuthoringResponse> {
    return httpRequest<AssignmentAuthoringResponse>(
      `/assessments/courses/${courseId}/assignments`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  /**
   * [Giảng viên] Cập nhật cấu hình bài tập / đồ án
   */
  updateAssignment(
    assignmentId: string,
    payload: AssignmentUpdateRequest
  ): Promise<AssignmentAuthoringResponse> {
    return httpRequest<AssignmentAuthoringResponse>(
      `/assessments/assignments/${assignmentId}`,
      {
        method: "PUT",
        body: payload,
      }
    );
  },

  /**
   * [Giảng viên] Xuất bản bài tập từ trạng thái Bản nháp
   */
  publishAssignment(assignmentId: string): Promise<AssignmentAuthoringResponse> {
    return httpRequest<AssignmentAuthoringResponse>(
      `/assessments/assignments/${assignmentId}/publish`,
      {
        method: "POST",
      }
    );
  },

  /**
   * [Giảng viên] Xóa bài tập khi chưa có sinh viên nào nộp bài
   */
  deleteAssignment(assignmentId: string): Promise<AssignmentDeleteResponse> {
    return httpRequest<AssignmentDeleteResponse>(
      `/assessments/assignments/${assignmentId}`,
      {
        method: "DELETE",
      }
    );
  },

  /**
   * Lấy cấu trúc Rubric 4 mức độ và trạng thái đóng băng của bài tập
   */
  getRubric(assignmentId: string): Promise<RubricResponse> {
    return httpRequest<RubricResponse>(
      `/assessments/assignments/${assignmentId}/rubric`
    );
  },

  /**
   * [Giảng viên] Tạo mới hoặc cập nhật bảng Rubric 4 mức độ (tổng điểm bắt buộc 10.0)
   */
  saveRubric(
    assignmentId: string,
    payload: RubricSaveRequest
  ): Promise<RubricResponse> {
    return httpRequest<RubricResponse>(
      `/assessments/assignments/${assignmentId}/rubric`,
      {
        method: "PUT",
        body: payload,
      }
    );
  },

  /**
   * Lấy trạng thái ký cam kết liêm chính học thuật và danh sách 3 điều khoản
   */
  getIntegrityPledge(assignmentId: string): Promise<PledgeStatusResponse> {
    return httpRequest<PledgeStatusResponse>(
      `/assessments/assignments/${assignmentId}/integrity-pledge`
    );
  },

  /**
   * [Sinh viên] Ký xác nhận cam kết liêm chính học thuật điện tử (BR-11 / BR-PLG-02)
   */
  signIntegrityPledge(
    assignmentId: string,
    payload: PledgeSignRequest
  ): Promise<PledgeSignResponse> {
    return httpRequest<PledgeSignResponse>(
      `/assessments/assignments/${assignmentId}/integrity-pledge`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  // ----------------------------------------------------------------------
  // Milestones, Topics, Groups, Peer Review (TV3 Realigned)
  // ----------------------------------------------------------------------
  listMilestones(assignmentId: string): Promise<MilestoneResponse[]> {
    return httpRequest<MilestoneResponse[]>(`/assessments/assignments/${assignmentId}/milestones`);
  },

  saveMilestones(assignmentId: string, milestones: MilestoneCreateRequest[]): Promise<MilestoneResponse[]> {
    return httpRequest<MilestoneResponse[]>(`/assessments/assignments/${assignmentId}/milestones`, {
      method: "POST",
      body: milestones,
    });
  },

  listTopics(assignmentId: string): Promise<TopicResponse[]> {
    return httpRequest<TopicResponse[]>(`/assessments/assignments/${assignmentId}/topics`);
  },

  createTopic(assignmentId: string, payload: TopicCreateRequest): Promise<TopicResponse> {
    return httpRequest<TopicResponse>(`/assessments/assignments/${assignmentId}/topics`, {
      method: "POST",
      body: payload,
    });
  },

  createGroup(assignmentId: string, payload: GroupCreateRequest): Promise<StudentGroupResponse> {
    return httpRequest<StudentGroupResponse>(`/assessments/assignments/${assignmentId}/groups`, {
      method: "POST",
      body: payload,
    });
  },

  joinGroupByCode(assignmentId: string, joinCode: string): Promise<StudentGroupResponse> {
    return httpRequest<StudentGroupResponse>(`/assessments/assignments/${assignmentId}/groups/join`, {
      method: "POST",
      body: { join_code: joinCode },
    });
  },

  selectGroupTopic(groupId: string, topicId: string): Promise<StudentGroupResponse> {
    return httpRequest<StudentGroupResponse>(`/assessments/groups/${groupId}/topic`, {
      method: "POST",
      body: { topic_id: topicId },
    });
  },

  autoAssignGroups(assignmentId: string): Promise<StudentGroupResponse[]> {
    return httpRequest<StudentGroupResponse[]>(`/assessments/assignments/${assignmentId}/groups/auto-assign`, {
      method: "POST",
    });
  },

  listGroups(assignmentId: string): Promise<StudentGroupResponse[]> {
    return httpRequest<StudentGroupResponse[]>(`/assessments/assignments/${assignmentId}/groups`);
  },

  getMyGroup(assignmentId: string): Promise<StudentGroupResponse> {
    return httpRequest<StudentGroupResponse>(`/assessments/assignments/${assignmentId}/groups/my-group`);
  },

  submitPeerReview(assignmentId: string, payload: PeerReviewSubmitRequest): Promise<PeerReviewResponse> {
    return httpRequest<PeerReviewResponse>(`/assessments/assignments/${assignmentId}/peer-reviews`, {
      method: "POST",
      body: payload,
    });
  },

  getPeerReviewFactors(assignmentId: string, groupId: string, milestoneId?: string): Promise<PeerReviewSummaryResponse> {
    const qs = milestoneId ? `?milestone_id=${encodeURIComponent(milestoneId)}` : "";
    return httpRequest<PeerReviewSummaryResponse>(
      `/assessments/assignments/${assignmentId}/groups/${groupId}/peer-reviews/factors${qs}`
    );
  },
};
