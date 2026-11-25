/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type {
  ActiveSessionResponse,
  AttemptResultResponse,
  AttemptStartRequest,
  AttemptStartResponse,
  AutosaveRequest,
  AutosaveResponse,
  PasscodeRegenerateResponse,
  PublishGradesResponse,
  QuestionBankCreate,
  QuestionBankResponse,
  QuestionCreate,
  QuestionDeleteResponse,
  QuestionResponse,
  QuestionUpdate,
  QuizCreate,
  QuizDetailResponse,
  QuizSettingsUpdate,
  QuizSummaryResponse,
  RegradeCreateRequest,
  RegradeReviewRequest,
  RegradeReviewResponse,
  RegradeStatus,
  RegradeSummaryResponse,
  SubmitAttemptRequest,
  SubmitAttemptResponse,
} from "../types/examination";
import { httpRequest } from "./httpClient";

const BASE = "/examinations";

export const examinationService = {
  // ------------------------------------------------------------------
  // Question Banks (T2-P-M4-01)
  // ------------------------------------------------------------------
  listQuestionBanks(courseId: string): Promise<QuestionBankResponse[]> {
    return httpRequest<QuestionBankResponse[]>(
      `${BASE}/courses/${courseId}/question-banks`
    );
  },

  createQuestionBank(
    courseId: string,
    payload: QuestionBankCreate
  ): Promise<QuestionBankResponse> {
    return httpRequest<QuestionBankResponse>(
      `${BASE}/courses/${courseId}/question-banks`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  deleteQuestionBank(bankId: string): Promise<void> {
    return httpRequest<void>(`${BASE}/question-banks/${bankId}`, {
      method: "DELETE",
    });
  },

  // ------------------------------------------------------------------
  // Questions (T2-P-M4-01)
  // ------------------------------------------------------------------
  listQuestions(
    courseId: string,
    params?: {
      bank_id?: string;
      lo_id?: string;
      bloom_level?: string;
      q?: string;
    }
  ): Promise<QuestionResponse[]> {
    const query = new URLSearchParams();
    if (params?.bank_id) query.set("bank_id", params.bank_id);
    if (params?.lo_id) query.set("lo_id", params.lo_id);
    if (params?.bloom_level) query.set("bloom_level", params.bloom_level);
    if (params?.q) query.set("q", params.q);
    const qs = query.toString();
    return httpRequest<QuestionResponse[]>(
      `${BASE}/courses/${courseId}/questions${qs ? `?${qs}` : ""}`
    );
  },

  createQuestion(
    courseId: string,
    payload: QuestionCreate
  ): Promise<QuestionResponse> {
    return httpRequest<QuestionResponse>(
      `${BASE}/courses/${courseId}/questions`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  updateQuestion(
    questionId: string,
    payload: QuestionUpdate
  ): Promise<QuestionResponse> {
    return httpRequest<QuestionResponse>(`${BASE}/questions/${questionId}`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteQuestion(questionId: string): Promise<QuestionDeleteResponse> {
    return httpRequest<QuestionDeleteResponse>(
      `${BASE}/questions/${questionId}`,
      {
        method: "DELETE",
      }
    );
  },

  // ------------------------------------------------------------------
  // Quizzes, Snapshots & Security Room Settings (T2-P-M4-01..02)
  // ------------------------------------------------------------------
  listQuizzes(courseId: string): Promise<QuizSummaryResponse[]> {
    return httpRequest<QuizSummaryResponse[]>(
      `${BASE}/courses/${courseId}/quizzes`
    );
  },

  createQuiz(
    courseId: string,
    payload: QuizCreate
  ): Promise<QuizDetailResponse> {
    return httpRequest<QuizDetailResponse>(
      `${BASE}/courses/${courseId}/quizzes`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  getQuizDetail(quizId: string): Promise<QuizDetailResponse> {
    return httpRequest<QuizDetailResponse>(`${BASE}/quizzes/${quizId}`);
  },

  updateQuizSettings(
    quizId: string,
    payload: QuizSettingsUpdate
  ): Promise<QuizDetailResponse> {
    return httpRequest<QuizDetailResponse>(
      `${BASE}/quizzes/${quizId}/settings`,
      {
        method: "PUT",
        body: payload,
      }
    );
  },

  publishQuiz(quizId: string): Promise<QuizDetailResponse> {
    return httpRequest<QuizDetailResponse>(
      `${BASE}/quizzes/${quizId}/publish`,
      {
        method: "POST",
      }
    );
  },

  regeneratePasscode(quizId: string): Promise<PasscodeRegenerateResponse> {
    return httpRequest<PasscodeRegenerateResponse>(
      `${BASE}/quizzes/${quizId}/passcode/regenerate`,
      {
        method: "POST",
      }
    );
  },

  publishGrades(quizId: string): Promise<PublishGradesResponse> {
    return httpRequest<PublishGradesResponse>(
      `${BASE}/quizzes/${quizId}/publish-grades`,
      {
        method: "POST",
      }
    );
  },

  // ------------------------------------------------------------------
  // Exam Taking, Resume Exam, Autosave & Active Session (T2-P-M4-03)
  // ------------------------------------------------------------------
  startOrResumeAttempt(
    quizId: string,
    payload?: AttemptStartRequest
  ): Promise<AttemptStartResponse> {
    return httpRequest<AttemptStartResponse>(
      `${BASE}/quizzes/${quizId}/attempts/start`,
      {
        method: "POST",
        body: payload ?? {},
      }
    );
  },

  autosaveAttempt(
    submissionId: string,
    payload: AutosaveRequest
  ): Promise<AutosaveResponse> {
    return httpRequest<AutosaveResponse>(
      `${BASE}/attempts/${submissionId}/autosave`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  submitAttempt(
    submissionId: string,
    payload?: SubmitAttemptRequest
  ): Promise<SubmitAttemptResponse> {
    return httpRequest<SubmitAttemptResponse>(
      `${BASE}/attempts/${submissionId}/submit`,
      {
        method: "POST",
        body: payload ?? {},
      }
    );
  },

  getActiveSession(quizId: string): Promise<ActiveSessionResponse> {
    return httpRequest<ActiveSessionResponse>(
      `${BASE}/quizzes/${quizId}/active-session`
    );
  },

  // ------------------------------------------------------------------
  // Results & 48-Hour Regrade Workflow (T2-P-M4-04)
  // ------------------------------------------------------------------
  getAttemptResult(submissionId: string): Promise<AttemptResultResponse> {
    return httpRequest<AttemptResultResponse>(
      `${BASE}/attempts/${submissionId}/result`
    );
  },

  createRegradeRequest(
    submissionId: string,
    payload: RegradeCreateRequest
  ): Promise<RegradeSummaryResponse> {
    return httpRequest<RegradeSummaryResponse>(
      `${BASE}/attempts/${submissionId}/regrades`,
      {
        method: "POST",
        body: payload,
      }
    );
  },

  listQuizRegrades(
    quizId: string,
    status?: RegradeStatus
  ): Promise<RegradeSummaryResponse[]> {
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    const qs = query.toString();
    return httpRequest<RegradeSummaryResponse[]>(
      `${BASE}/quizzes/${quizId}/regrades${qs ? `?${qs}` : ""}`
    );
  },

  reviewRegradeRequest(
    regradeId: string,
    payload: RegradeReviewRequest
  ): Promise<RegradeReviewResponse> {
    return httpRequest<RegradeReviewResponse>(
      `${BASE}/regrades/${regradeId}/review`,
      {
        method: "POST",
        body: payload,
      }
    );
  },
};
