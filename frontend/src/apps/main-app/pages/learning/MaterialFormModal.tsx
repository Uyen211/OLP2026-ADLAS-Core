/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, FileText, Film, Presentation } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LOResponse } from "../../../../types/course";
import type { LearningMaterial, MaterialType } from "../../../../types/learning";
import { FileDropzone } from "../../components/FileDropzone";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string; icon: React.ReactNode }> = [
  { value: "SLIDE", label: "Bài giảng trình chiếu (Slide PPTX/PPT)", icon: <Presentation className="h-4 w-4" /> },
  { value: "PDF", label: "Tài liệu chuyên đề (PDF)", icon: <FileText className="h-4 w-4" /> },
  { value: "VIDEO", label: "Video bài giảng (MP4 / WebM)", icon: <Film className="h-4 w-4" /> },
  { value: "DOCUMENT", label: "Tài liệu văn bản (Word / Markdown / TXT)", icon: <FileText className="h-4 w-4" /> },
];

export interface MaterialFormModalProps {
  open: boolean;
  courseId: string;
  moduleId: string;
  availableLos: LOResponse[];
  editingMaterial?: LearningMaterial | null;
  onClose: () => void;
  onSaved: (mat: LearningMaterial) => void;
}

export const MaterialFormModal: React.FC<MaterialFormModalProps> = ({
  open,
  courseId,
  moduleId,
  availableLos,
  editingMaterial,
  onClose,
  onSaved,
}) => {
  const [title, setTitle] = useState("");
  const [materialType, setMaterialType] = useState<MaterialType>("SLIDE");
  const [loId, setLoId] = useState<string>("");
  const [estDuration, setEstDuration] = useState<number>(30);
  const [isMandatory, setIsMandatory] = useState(true);
  const [isPublished, setIsPublished] = useState(true);
  const [fileUrl, setFileUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(false);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingMaterial) {
      setTitle(editingMaterial.title);
      setMaterialType(editingMaterial.material_type);
      setLoId(editingMaterial.lo_id ?? "");
      setEstDuration(editingMaterial.est_duration_minutes ?? 30);
      setIsMandatory(editingMaterial.is_mandatory);
      setIsPublished(editingMaterial.is_published);
      setFileUrl(editingMaterial.file_url ?? "");
      setSelectedFile(null);
    } else {
      setTitle("");
      setMaterialType("SLIDE");
      setLoId("");
      setEstDuration(30);
      setIsMandatory(true);
      setIsPublished(true);
      setFileUrl("");
      setSelectedFile(null);
    }
    setTitleError(null);
    setBannerError(null);
  }, [open, editingMaterial]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setTitleError("Vui lòng nhập tiêu đề học liệu.");
      return;
    }

    setLoading(true);
    setBannerError(null);

    // Client-side BR-STORAGE-02 file size pre-validation
    if (selectedFile) {
      const isVideo = materialType === "VIDEO" || selectedFile.type.startsWith("video/");
      const maxBytes = isVideo ? 500 * 1024 * 1024 : 50 * 1024 * 1024;
      const maxMbText = isVideo ? "500MB" : "50MB";
      if (selectedFile.size > maxBytes) {
        const actualMb = (selectedFile.size / (1024 * 1024)).toFixed(1);
        setBannerError(`Kích thước tệp (${actualMb} MB) vượt quá giới hạn ${maxMbText} quy định tại BR-STORAGE-02.`);
        setLoading(false);
        return;
      }
    }

    try {
      let finalFileUrl = fileUrl.trim();

      // If user uploaded a new file, upload to server first
      if (selectedFile) {
        setUploadProgress(true);
        const uploadRes = await learningService.uploadMaterialFile(courseId, moduleId, selectedFile);
        finalFileUrl = uploadRes.file_url;
        setUploadProgress(false);
      }

      const selectedLoId = loId ? loId : null;

      if (editingMaterial) {
        const updated = await learningService.updateMaterial(courseId, editingMaterial.id, {
          title: title.trim(),
          material_type: materialType,
          lo_id: selectedLoId,
          file_url: finalFileUrl || null,
          is_mandatory: isMandatory,
          est_duration_minutes: Number(estDuration) || 30,
          is_published: isPublished,
        });
        showToast("success", `Đã cập nhật học liệu: ${updated.title}`);
        onSaved(updated);
      } else {
        const created = await learningService.createMaterial(courseId, moduleId, {
          title: title.trim(),
          material_type: materialType,
          lo_id: selectedLoId,
          file_url: finalFileUrl || null,
          is_mandatory: isMandatory,
          est_duration_minutes: Number(estDuration) || 30,
          is_published: isPublished,
        });
        showToast("success", `Đã thêm học liệu mới: ${created.title}`);
        onSaved(created);
      }
      onClose();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Đã xảy ra lỗi khi lưu học liệu.";
      setBannerError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
      setUploadProgress(false);
    }
  };

  return (
    <MmModal
      open={open}
      title={editingMaterial ? "Chỉnh sửa học liệu số" : "Thêm học liệu bài giảng"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {bannerError && (
          <div className="flex items-center gap-2 rounded-mm bg-mm-error-bg p-3 text-sm text-mm-error">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{bannerError}</span>
          </div>
        )}

        <FormField label="Tiêu đề học liệu" htmlFor="mat-title" required error={titleError}>
          <input
            id="mat-title"
            type="text"
            className={mmInputClass(Boolean(titleError))}
            placeholder="Ví dụ: Slide Bài giảng: Kiến trúc DX-OS Open-Core"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Loại học liệu" htmlFor="mat-type">
            <select
              id="mat-type"
              className={mmInputClass()}
              value={materialType}
              onChange={(e) => setMaterialType(e.target.value as MaterialType)}
            >
              {MATERIAL_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </FormField>

          <FormField
            label="Chuẩn đầu ra gắn kết (LO)"
            htmlFor="mat-lo"
            helper="Gắn với Chuẩn đầu ra để theo dõi tiến độ (BR-LO-01)."
          >
            <select
              id="mat-lo"
              className={mmInputClass()}
              value={loId}
              onChange={(e) => setLoId(e.target.value)}
            >
              <option value="">-- Chưa liên kết Chuẩn đầu ra --</option>
              {availableLos.map((lo) => (
                <option key={lo.id} value={lo.id}>
                  {lo.code} - {lo.description} ({lo.bloom_level})
                </option>
              ))}
            </select>
          </FormField>
        </div>

        <FormField
          label="Tệp đính kèm học liệu (Upload file)"
          helper="Slide/PDF tối đa 50MB; Video tối đa 500MB (Quy tắc BR-STORAGE-02)."
        >
          <FileDropzone
            accept=".pdf,.pptx,.ppt,.mp4,.webm,.docx,.doc,.txt,.md"
            file={selectedFile}
            onFileSelect={setSelectedFile}
            helperText="Kéo thả hoặc chọn tệp PDF, PPTX, MP4, DOCX hoặc Markdown"
          />
          {fileUrl && !selectedFile && (
            <div className="mt-1.5 flex items-center justify-between gap-2 rounded bg-mm-surface-alt/60 px-2.5 py-1 text-xs">
              <span className="truncate text-mm-text-muted">
                Đường dẫn hiện tại: <span className="font-mono text-mm-text-primary">{fileUrl}</span>
              </span>
              <button
                type="button"
                onClick={() => setFileUrl("")}
                className="shrink-0 font-medium text-mm-error hover:underline"
              >
                Gỡ bỏ tệp
              </button>
            </div>
          )}
        </FormField>

        {materialType === "VIDEO" && (
          <FormField
            label="Hoặc Đường dẫn Video trực tuyến (URL)"
            htmlFor="mat-url"
            helper="Hỗ trợ link video MP4/HLS/YouTube trực tiếp"
          >
            <input
              id="mat-url"
              type="text"
              className={mmInputClass()}
              placeholder="https://..."
              value={fileUrl}
              onChange={(e) => setFileUrl(e.target.value)}
            />
          </FormField>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Thời lượng học dự kiến (phút)" htmlFor="mat-duration">
            <input
              id="mat-duration"
              type="number"
              min={1}
              max={1440}
              className={mmInputClass()}
              value={estDuration}
              onChange={(e) => setEstDuration(Number(e.target.value))}
            />
          </FormField>

          <div className="flex flex-col justify-center space-y-2 pt-4">
            <label className="flex items-center gap-2 cursor-pointer font-mm-ui text-sm text-mm-text-primary">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-mm-divider text-mm-brand focus:ring-mm-brand"
                checked={isMandatory}
                onChange={(e) => setIsMandatory(e.target.checked)}
              />
              <span>Học liệu bắt buộc hoàn thành</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer font-mm-ui text-sm text-mm-text-primary">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-mm-divider text-mm-brand focus:ring-mm-brand"
                checked={isPublished}
                onChange={(e) => setIsPublished(e.target.checked)}
              />
              <span>Công bố ngay cho sinh viên</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-mm-divider">
          <MmButton variant="secondary" type="button" onClick={onClose} disabled={loading}>
            Hủy
          </MmButton>
          <MmButton variant="brand" type="submit" disabled={loading}>
            {uploadProgress
              ? "Đang tải tệp lên..."
              : loading
              ? "Đang lưu..."
              : editingMaterial
              ? "Cập nhật"
              : "Thêm học liệu"}
          </MmButton>
        </div>
      </form>
    </MmModal>
  );
};
