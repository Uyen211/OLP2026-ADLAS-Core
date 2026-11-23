/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, KeyRound } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { CourseSummary } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface JoinCourseModalProps {
  open: boolean;
  onClose: () => void;
  onJoined: (course: CourseSummary) => void;
}

export const JoinCourseModal: React.FC<JoinCourseModalProps> = ({
  open,
  onClose,
  onJoined,
}) => {
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setJoinCode("");
    setError(null);
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleaned = joinCode.trim().toUpperCase().replace(/\s+/g, "");
    if (cleaned.length < 6) {
      setError("Vui lòng nhập đầy đủ mã vào lớp gồm 6 ký tự.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const course = await courseService.joinByCode(cleaned);
      showToast("success", `Bạn đã tham gia lớp ${course.course_code} - ${course.name}!`);
      setJoinCode("");
      onJoined(course);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Không thể tham gia lớp học. Vui lòng kiểm tra lại mã vào lớp.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Tham gia lớp học bằng mã"
      subtitle="Nhập mã 6 ký tự do giảng viên cung cấp để ghi danh vào lớp"
      onClose={handleClose}
      maxWidthClass="max-w-md"
      footer={
        <>
          <MmButton variant="secondary" onClick={handleClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton type="submit" form="join-course-form" variant="brand" loading={loading}>
            <KeyRound className="h-4 w-4" />
            <span>Tham gia lớp</span>
          </MmButton>
        </>
      }
    >
      {error && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{error}</span>
        </div>
      )}

      <form id="join-course-form" onSubmit={handleSubmit} noValidate>
        <FormField
          label="Mã vào lớp (Join Code)"
          htmlFor="join-code-input"
          required
          helper="Mã gồm 6 ký tự chữ in hoa và số, không phân biệt chữ hoa/thường"
        >
          <input
            id="join-code-input"
            type="text"
            maxLength={10}
            value={joinCode}
            onChange={(e) => {
              setJoinCode(e.target.value.toUpperCase());
              if (error) setError(null);
            }}
            placeholder="VD: K9M2PX"
            className={`${mmInputClass(Boolean(error))} text-center font-mm-mono text-xl tracking-[0.25em]`}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
