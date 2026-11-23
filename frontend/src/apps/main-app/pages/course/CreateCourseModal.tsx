/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { CourseDetail } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface CreateCourseModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (course: CourseDetail) => void;
}

export const CreateCourseModal: React.FC<CreateCourseModalProps> = ({
  open,
  onClose,
  onCreated,
}) => {
  const today = new Date().toISOString().slice(0, 10);
  const defaultEnd = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const [courseCode, setCourseCode] = useState("");
  const [sectionCode, setSectionCode] = useState("N01");
  const [name, setName] = useState("");
  const [semester, setSemester] = useState("HK1-2026");
  const [credits, setCredits] = useState(3);
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [isTemplate, setIsTemplate] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const resetForm = () => {
    setCourseCode("");
    setSectionCode("N01");
    setName("");
    setSemester("HK1-2026");
    setCredits(3);
    setStartDate(today);
    setEndDate(defaultEnd);
    setIsTemplate(false);
    setErrorBanner(null);
    setFieldErrors({});
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const errs: Record<string, string> = {};
    const normalizedCode = courseCode.trim().toUpperCase();

    if (!normalizedCode) {
      errs.course_code = "Vui lòng nhập mã môn học.";
    } else if (!/^[A-Z0-9_-]{2,30}$/.test(normalizedCode)) {
      errs.course_code = "Mã môn học chỉ gồm chữ in hoa, số, dấu gạch ngang hoặc gạch dưới.";
    }
    if (!sectionCode.trim()) errs.section_code = "Vui lòng nhập mã lớp học phần.";
    if (name.trim().length < 3) errs.name = "Tên môn học phải có ít nhất 3 ký tự.";
    if (!semester.trim()) errs.semester = "Vui lòng nhập học kỳ.";
    if (credits < 1 || credits > 6) errs.credits = "Số tín chỉ phải từ 1 đến 6.";

    const startMs = Date.parse(startDate);
    const endMs = Date.parse(endDate);
    if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs - startMs < 7 * 86400000) {
      errs.end_date = "Ngày kết thúc phải sau ngày bắt đầu ít nhất 7 ngày.";
    }

    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      setErrorBanner(null);
      return;
    }

    setFieldErrors({});
    setErrorBanner(null);
    setLoading(true);

    try {
      const created = await courseService.createCourse({
        course_code: normalizedCode,
        section_code: sectionCode.trim(),
        name: name.trim(),
        semester: semester.trim(),
        credits,
        start_date: startDate,
        end_date: endDate,
        is_template: isTemplate,
      });
      showToast("success", `Đã tạo môn học ${created.course_code} thành công!`);
      resetForm();
      onCreated(created);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.field) {
          setFieldErrors({ [err.field]: err.message });
        }
        setErrorBanner(err.message);
      } else {
        setErrorBanner("Không thể tạo môn học mới. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Tạo môn học mới"
      subtitle="Thiết lập thông tin cơ bản cho lớp học phần hoặc môn học mẫu"
      onClose={handleClose}
      maxWidthClass="max-w-xl"
      footer={
        <>
          <MmButton variant="secondary" onClick={handleClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton
            type="submit"
            form="create-course-form"
            variant="brand"
            loading={loading}
          >
            Tạo môn học
          </MmButton>
        </>
      }
    >
      {errorBanner && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{errorBanner}</span>
        </div>
      )}

      <form id="create-course-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Mã môn học"
            htmlFor="create-course-code"
            required
            error={fieldErrors.course_code}
            helper="Tự động viết hoa, vd: IT3080"
          >
            <input
              id="create-course-code"
              type="text"
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
              placeholder="IT3080"
              className={mmInputClass(Boolean(fieldErrors.course_code))}
            />
          </FormField>

          <FormField
            label="Mã lớp học phần"
            htmlFor="create-section-code"
            required
            error={fieldErrors.section_code}
          >
            <input
              id="create-section-code"
              type="text"
              value={sectionCode}
              onChange={(e) => setSectionCode(e.target.value)}
              placeholder="N01"
              className={mmInputClass(Boolean(fieldErrors.section_code))}
            />
          </FormField>
        </div>

        <FormField label="Tên môn học" htmlFor="create-course-name" required error={fieldErrors.name}>
          <input
            id="create-course-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="vd: Mạng máy tính và Truyền thông"
            className={mmInputClass(Boolean(fieldErrors.name))}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Học kỳ" htmlFor="create-semester" required error={fieldErrors.semester}>
            <input
              id="create-semester"
              type="text"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              placeholder="HK1-2026"
              className={mmInputClass(Boolean(fieldErrors.semester))}
            />
          </FormField>

          <FormField label="Số tín chỉ" htmlFor="create-credits" required error={fieldErrors.credits}>
            <input
              id="create-credits"
              type="number"
              min={1}
              max={6}
              value={credits}
              onChange={(e) => setCredits(Number(e.target.value))}
              className={mmInputClass(Boolean(fieldErrors.credits))}
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Ngày bắt đầu" htmlFor="create-start-date" required>
            <input
              id="create-start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={mmInputClass(false)}
            />
          </FormField>

          <FormField
            label="Ngày kết thúc"
            htmlFor="create-end-date"
            required
            error={fieldErrors.end_date}
          >
            <input
              id="create-end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={mmInputClass(Boolean(fieldErrors.end_date))}
            />
          </FormField>
        </div>

        <label className="flex cursor-pointer items-center gap-2.5 rounded-mm-panel border border-mm-border bg-mm-divider/40 px-4 py-3">
          <input
            type="checkbox"
            checked={isTemplate}
            onChange={(e) => setIsTemplate(e.target.checked)}
            className="h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
          />
          <div>
            <span className="block font-mm-ui text-sm font-medium text-mm-heading">
              Đánh dấu là Môn học mẫu (Template)
            </span>
            <span className="block font-mm-ui text-xs text-mm-text-helper">
              Môn mẫu dùng để sao chép đề cương và chuẩn đầu ra sang các học kỳ mới, không nhận sinh viên ghi danh.
            </span>
          </div>
        </label>
      </form>
    </MmModal>
  );
};
