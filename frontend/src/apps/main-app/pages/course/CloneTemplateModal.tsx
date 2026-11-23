/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, Copy, Info } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { CourseDetail, CourseSummary } from "../../../../types/course";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface CloneTemplateModalProps {
  open: boolean;
  mode: "create-course" | "import-into-course";
  targetCourseId?: string;
  onClose: () => void;
  onClonedCourse?: (course: CourseDetail) => void;
  onImportedSyllabus?: () => void;
}

export const CloneTemplateModal: React.FC<CloneTemplateModalProps> = ({
  open,
  mode,
  targetCourseId,
  onClose,
  onClonedCourse,
  onImportedSyllabus,
}) => {
  const today = new Date().toISOString().slice(0, 10);
  const defaultEnd = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const [templates, setTemplates] = useState<CourseSummary[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [sectionCode, setSectionCode] = useState("N01");
  const [semester, setSemester] = useState("HK1-2026");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setLoadingTemplates(true);
    courseService
      .listTemplates()
      .then((list) => {
        setTemplates(list);
        if (list.length > 0) {
          setSelectedTemplateId(list[0].id);
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Không thể tải danh sách môn mẫu.");
      })
      .finally(() => setLoadingTemplates(false));
  }, [open]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedTemplateId) {
      setError("Vui lòng chọn một môn học mẫu.");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      if (mode === "create-course") {
        const created = await courseService.cloneCourse({
          template_id: selectedTemplateId,
          section_code: sectionCode.trim(),
          semester: semester.trim(),
          start_date: startDate,
          end_date: endDate,
        });
        showToast("success", `Đã nhân bản lớp ${created.course_code} - ${created.section_code} thành công!`);
        onClonedCourse?.(created);
      } else if (targetCourseId) {
        const result = await courseService.importSyllabusTemplate(
          targetCourseId,
          selectedTemplateId
        );
        const skippedNote =
          result.skipped_duplicate_codes.length > 0
            ? ` (bỏ qua ${result.skipped_duplicate_codes.length} mã LO trùng)`
            : "";
        showToast(
          "success",
          `Đã nạp đề cương và ${result.copied_los} chuẩn đầu ra từ môn mẫu${skippedNote}.`
        );
        onImportedSyllabus?.();
      }
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thể sao chép từ môn mẫu.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <MmModal
      open={open}
      title={
        mode === "create-course"
          ? "Tạo lớp học mới từ Môn mẫu"
          : "Nạp đề cương & Chuẩn đầu ra từ Môn mẫu"
      }
      subtitle="Tái sử dụng nhanh nội dung đào tạo giữa các học kỳ"
      onClose={onClose}
      maxWidthClass="max-w-lg"
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={submitting}>
            Hủy bỏ
          </MmButton>
          <MmButton
            type="submit"
            form="clone-template-form"
            variant="brand"
            loading={submitting}
            disabled={loadingTemplates || templates.length === 0}
          >
            <Copy className="h-4 w-4" />
            <span>{mode === "create-course" ? "Tạo lớp từ mẫu" : "Nạp đề cương"}</span>
          </MmButton>
        </>
      }
    >
      <div className="mb-4 flex items-start gap-2.5 rounded-mm-panel border border-mm-blue-light bg-mm-blue-light/25 px-4 py-3 text-mm-blue-deep">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <p className="font-mm-ui text-xs leading-relaxed">
          Chỉ sao chép đề cương, số tín chỉ và danh mục Chuẩn đầu ra (LO).{" "}
          <span className="font-semibold">
            Không sao chép danh sách sinh viên và điểm số cũ (BR-03).
          </span>
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{error}</span>
        </div>
      )}

      {loadingTemplates ? (
        <p className="py-6 text-center font-mm-ui text-sm text-mm-text-muted">
          Đang tải danh sách môn học mẫu...
        </p>
      ) : templates.length === 0 ? (
        <p className="py-6 text-center font-mm-ui text-sm text-mm-text-secondary">
          Chưa có môn học mẫu nào trong hệ thống. Hãy tạo một môn mới và đánh dấu là Môn học mẫu trước.
        </p>
      ) : (
        <form id="clone-template-form" onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Chọn môn học mẫu" htmlFor="clone-template-select" required>
            <select
              id="clone-template-select"
              value={selectedTemplateId}
              onChange={(e) => setSelectedTemplateId(e.target.value)}
              className={mmInputClass(false)}
            >
              {templates.map((tpl) => (
                <option key={tpl.id} value={tpl.id}>
                  {tpl.course_code} - {tpl.name} ({tpl.lo_count} LO, {tpl.credits} TC)
                </option>
              ))}
            </select>
          </FormField>

          {mode === "create-course" && (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Mã lớp học phần mới" htmlFor="clone-section" required>
                  <input
                    id="clone-section"
                    type="text"
                    value={sectionCode}
                    onChange={(e) => setSectionCode(e.target.value)}
                    placeholder="N01"
                    className={mmInputClass(false)}
                  />
                </FormField>

                <FormField label="Học kỳ áp dụng" htmlFor="clone-semester" required>
                  <input
                    id="clone-semester"
                    type="text"
                    value={semester}
                    onChange={(e) => setSemester(e.target.value)}
                    placeholder="HK1-2026"
                    className={mmInputClass(false)}
                  />
                </FormField>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Ngày bắt đầu" htmlFor="clone-start" required>
                  <input
                    id="clone-start"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className={mmInputClass(false)}
                  />
                </FormField>

                <FormField label="Ngày kết thúc" htmlFor="clone-end" required>
                  <input
                    id="clone-end"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className={mmInputClass(false)}
                  />
                </FormField>
              </div>
            </>
          )}
        </form>
      )}
    </MmModal>
  );
};
