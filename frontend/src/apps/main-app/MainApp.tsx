/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/outfit/500.css";
import "@fontsource/outfit/600.css";
import "@fontsource/poppins/500.css";
import "@fontsource/poppins/600.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "./theme/minimax.css";

import { authService } from "../../services/authService";
import { useAuthStore } from "../../stores/authStore";
import { ToastContainer } from "./components/Toast";
import { ForgotPasswordPage } from "./pages/auth/ForgotPasswordPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { MfaVerifyPage } from "./pages/auth/MfaVerifyPage";
import { ResetPasswordPage } from "./pages/auth/ResetPasswordPage";
import { CourseDetailPage } from "./pages/course/CourseDetailPage";
import { CourseListPage } from "./pages/course/CourseListPage";
import { StudentRosterPage } from "./pages/course/StudentRosterPage";
import { AssignmentDetailPage } from "./pages/assessment/AssignmentDetailPage";
import { RubricBuilderPage } from "./pages/assessment/RubricBuilderPage";
import { VivaSandboxPage } from "./pages/assessment/VivaSandboxPage";
import { ExamManagementPage } from "./pages/examination/ExamManagementPage";
import { ExamResultPage } from "./pages/examination/ExamResultPage";
import { ExamTakingPage } from "./pages/examination/ExamTakingPage";
import { GradeReportPage } from "./pages/reports/GradeReportPage";

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export const MainApp: React.FC = () => {
  const { accessToken, setMe, clearSession } = useAuthStore();

  useEffect(() => {
    if (!accessToken) return;
    authService
      .getMe()
      .then((profile) => setMe(profile))
      .catch(() => {
        // httpClient handles 401 refresh; if still invalid, clear session
        if (!useAuthStore.getState().accessToken) {
          clearSession();
        }
      });
  }, [accessToken, setMe, clearSession]);

  return (
    <div className="mm-root">
      <ToastContainer />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/mfa-verify" element={<MfaVerifyPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        <Route
          path="/courses"
          element={
            <ProtectedRoute>
              <CourseListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId"
          element={
            <ProtectedRoute>
              <CourseDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/roster"
          element={
            <ProtectedRoute>
              <StudentRosterPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/assignments/:assignmentId"
          element={
            <ProtectedRoute>
              <AssignmentDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/assignments/:assignmentId/rubric"
          element={
            <ProtectedRoute>
              <RubricBuilderPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/reports"
          element={
            <ProtectedRoute>
              <GradeReportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/assignments/:assignmentId"
          element={
            <ProtectedRoute>
              <AssignmentDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/viva/:submissionId"
          element={
            <ProtectedRoute>
              <VivaSandboxPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/exams"
          element={
            <ProtectedRoute>
              <ExamManagementPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/exams/:quizId/take"
          element={
            <ProtectedRoute>
              <ExamTakingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/exams/:quizId/result"
          element={
            <ProtectedRoute>
              <ExamResultPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="*"
          element={
            accessToken ? (
              <Navigate to="/courses" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </div>
  );
};
