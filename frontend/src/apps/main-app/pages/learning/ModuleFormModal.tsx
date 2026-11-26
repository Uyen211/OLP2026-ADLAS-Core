/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { LearningModule } from "../../../../types/learning";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface ModuleFormModalProps {
  open: boolean;
  courseId: string;
  existingModules: LearningModule[];
  editingModule?: LearningModule | null;
  onClose: () => void;
  onSaved: (mod: LearningModule) => void;
}

export const ModuleFormModal: React.FC<ModuleFormModalProps> = ({
  open,
  courseId,
  existingModules,
  editingModule,
  onClose,
  onSaved,
}) => {
  const [title, setTitle] = useState("");
  const [unlockAt, setUnlockAt] = useState("");
  const [prerequisiteModuleId, setPrerequisiteModuleId] = useState<string>("");
  const [isPublished, setIsPublished] = useState(false);
  const [loading, setLoading] = useState(false);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingModule) {
      setTitle(editingModule.title);
      setUnlockAt(
        editingModule.unlock_at
          ? new Date(editingModule.unlock_at).toISOString().slice(0, 16)
          : ""
      );
      setPrerequisiteModuleId(editingModule.prerequisite_module_id ?? "");
      setIsPublished(editingModule.is_published);
    } else {
      setTitle("");
      setUnlockAt("");
      setPrerequisiteModuleId("");
      setIsPublished(false);
    }
    setTitleError(null);
    setBannerError(null);
  }, [open, editingModule]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setTitleError("Vui lòng nhập tiêu đề chương/bài học.");
      return;
    }

    setLoading(true);
    setBannerError(null);

    const unlockIso = unlockAt ? new Date(unlockAt).toISOString() : null;
    const prereqId = prerequisiteModuleId ? prerequisiteModuleId : null;

    try {
      if (editingModule) {
        const updated = await learningService.updateModule(courseId, editingModule.id, {
          title: title.trim(),
          unlock_at: unlockIso,
          prerequisite_module_id: prereqId,
          is_published: isPublished,
        });
        showToast("success", `Đã cập nhật bài học: ${updated.title}`);
        onSaved(updated);
      } else {
        const created = await learningService.createModule(courseId, {
          title: title.trim(),
          unlock_at: unlockIso,
          prerequisite_module_id: prereqId,
          is_published: isPublished,
        });
        showToast("success", `Đã tạo bài học mới: ${created.title}`);
        onSaved(created);
      }
      onClose();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Đã xảy ra lỗi khi lưu bài học.";
      setBannerError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  };

  // Filter out self to prevent self-prerequisite in dropdown
  const availablePrereqs = existingModules.filter(
    (m) => !editingModule || m.id !== editingModule.id
  );

  return (
    <MmModal
      open={open}
      title={editingModule ? "Chỉnh sửa chương/bài học" : "Tạo chương/bài học mới"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {bannerError && (
          <div className="flex items-center gap-2 rounded-mm bg-mm-error-bg p-3 text-sm text-mm-error">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{bannerError}</span>
          </div>
        )}

        <FormField label="Tiêu đề chương/bài học" htmlFor="module-title" required error={titleError}>
          <input
            id="module-title"
            type="text"
            className={mmInputClass(Boolean(titleError))}
            placeholder="Ví dụ: Chương 1: Kiến trúc Hệ thống & RAG Tri thức"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
          />
        </FormField>

        <FormField
          label="Bài học tiên quyết (Bắt buộc hoàn thành trước)"
          htmlFor="module-prereq"
          helper="Sinh viên chỉ có thể mở khóa bài học này sau khi đã hoàn thành bài tiên quyết."
        >
          <select
            id="module-prereq"
            className={mmInputClass()}
            value={prerequisiteModuleId}
            onChange={(e) => setPrerequisiteModuleId(e.target.value)}
          >
            <option value="">-- Không có bài tiên quyết (Mở tự do) --</option>
            {availablePrereqs.map((m) => (
              <option key={m.id} value={m.id}>
                Thứ tự {m.order_index}: {m.title}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Thời điểm tự động mở khóa (Tùy chọn)"
          htmlFor="module-unlock"
          helper="Để trống nếu muốn bài học mở ngay khi sinh viên thỏa mãn điều kiện tiên quyết."
        >
          <input
            id="module-unlock"
            type="datetime-local"
            className={mmInputClass()}
            value={unlockAt}
            onChange={(e) => setUnlockAt(e.target.value)}
          />
        </FormField>

        <div className="flex items-center gap-3 pt-2">
          <input
            id="module-publish"
            type="checkbox"
            className="h-4 w-4 rounded border-mm-divider text-mm-brand focus:ring-mm-brand"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.target.checked)}
          />
          <label htmlFor="module-publish" className="font-mm-ui text-sm font-medium text-mm-text-primary">
            Xuất bản ngay cho sinh viên xem
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-mm-divider">
          <MmButton variant="secondary" type="button" onClick={onClose} disabled={loading}>
            Hủy
          </MmButton>
          <MmButton variant="brand" type="submit" disabled={loading}>
            {loading ? "Đang lưu..." : editingModule ? "Cập nhật" : "Tạo bài học"}
          </MmButton>
        </div>
      </form>
    </MmModal>
  );
};
