/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, UserPlus } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { RosterItemResponse } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface AddStudentModalProps {
  open: boolean;
  courseId: string;
  onClose: () => void;
  onAdded: (student: RosterItemResponse) => void;
}

export const AddStudentModal: React.FC<AddStudentModalProps> = ({
  open,
  courseId,
  onClose,
  onAdded,
}) => {
  const [userCode, setUserCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setUserCode("");
    setFullName("");
    setEmail("");
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!userCode.trim() || !fullName.trim() || !email.trim()) {
      setError("Vui lòng nhập đầy đủ MSSV, Họ và tên và Email.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const added = await courseService.addSingleStudent(courseId, {
        user_code: userCode.trim(),
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
      });
      showToast("success", `Đã thêm sinh viên ${added.full_name} vào lớp học.`);
      reset();
      onAdded(added);
      onClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Không thể thêm sinh viên vào lớp. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Thêm sinh viên vào lớp"
      subtitle="Hệ thống sẽ tự động tạo tài khoản nếu sinh viên chưa có trong ADLAS"
      onClose={handleClose}
      maxWidthClass="max-w-md"
      footer={
        <>
          <MmButton variant="secondary" onClick={handleClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton type="submit" form="add-student-form" variant="brand" loading={loading}>
            <UserPlus className="h-4 w-4" />
            <span>Thêm sinh viên</span>
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

      <form id="add-student-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField label="Mã số sinh viên (MSSV)" htmlFor="student-code" required>
          <input
            id="student-code"
            type="text"
            value={userCode}
            onChange={(e) => setUserCode(e.target.value)}
            placeholder="vd: 20260001"
            className={mmInputClass(false)}
          />
        </FormField>

        <FormField label="Họ và tên" htmlFor="student-name" required>
          <input
            id="student-name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="vd: Nguyễn Văn An"
            className={mmInputClass(false)}
          />
        </FormField>

        <FormField label="Email" htmlFor="student-email" required>
          <input
            id="student-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="vd: an.nv@adlas.edu.vn"
            className={mmInputClass(false)}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
