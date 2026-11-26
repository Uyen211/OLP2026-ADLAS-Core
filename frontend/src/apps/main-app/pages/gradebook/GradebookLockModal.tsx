/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertTriangle, Lock, Unlock, X } from "lucide-react";
import { gradebookService } from "../../../../services/gradebookService";
import { ApiError } from "../../../../services/httpClient";
import type { GradebookLockPreviewResponse } from "../../../../types/gradebook";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";

interface GradebookLockModalProps {
  open: boolean;
  mode: "lock" | "unlock";
  courseId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const GradebookLockModal: React.FC<GradebookLockModalProps> = ({
  open,
  mode,
  courseId,
  onClose,
  onSuccess,
}) => {
  const [preview, setPreview] = useState<GradebookLockPreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [decisionCode, setDecisionCode] = useState("");
  const [unlockReason, setUnlockReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setConfirmPhrase("");
    setDecisionCode("");
    setUnlockReason("");
    if (mode === "lock") {
      setLoadingPreview(true);
      gradebookService
        .getLockPreview(courseId)
        .then((res) => setPreview(res))
        .catch(() => setPreview(null))
        .finally(() => setLoadingPreview(false));
    }
  }, [open, mode, courseId]);

  if (!open) return null;

  const isExactPhrase = confirmPhrase === "KHOA DIEM";
  const hasMutedColumns = Boolean(preview && preview.muted_columns.length > 0);
  const canConfirmLock = isExactPhrase && !hasMutedColumns && !loadingPreview;

  const handleConfirmLock = async () => {
    if (!canConfirmLock) return;
    setSubmitting(true);
    try {
      await gradebookService.lockCourseGradebook(courseId, confirmPhrase);
      showToast("success", "Đã khóa niêm phong sổ điểm học phần thành công!");
      onSuccess();
      onClose();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể khóa sổ điểm.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (decisionCode.trim().length < 3 || unlockReason.trim().length < 30) {
      showToast("error", "Vui lòng nhập mã quyết định và lý do mở khóa tối thiểu 30 ký tự.");
      return;
    }
    setSubmitting(true);
    try {
      await gradebookService.emergencyUnlockGradebook(
        courseId,
        decisionCode.trim(),
        unlockReason.trim()
      );
      showToast("success", "Đã mở khóa sổ điểm khẩn cấp và ghi nhật ký kiểm toán.");
      onSuccess();
      onClose();
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Không thể mở khóa sổ điểm.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-xl rounded-2xl border border-mm-border bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between border-b border-mm-divider pb-4">
          <div className="flex items-center gap-2">
            {mode === "lock" ? (
              <Lock className="h-5 w-5 text-rose-600" />
            ) : (
              <Unlock className="h-5 w-5 text-amber-600" />
            )}
            <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
              {mode === "lock"
                ? "Khóa Niêm Phong Sổ Điểm Cuối Kỳ (Poka-Yoke)"
                : "Yêu Cầu Mở Khóa Chỉnh Sửa Khẩn Cấp (Subflow A-1)"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-mm-text-secondary hover:bg-mm-divider"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {mode === "lock" ? (
          <div className="mt-4 space-y-4">
            {loadingPreview ? (
              <p className="text-sm text-mm-text-secondary">Đang tổng hợp thống kê học vụ...</p>
            ) : preview ? (
              <div className="grid grid-cols-2 gap-3 rounded-xl border border-mm-divider bg-slate-50 p-4 text-xs sm:grid-cols-4">
                <div>
                  <p className="text-mm-text-muted">Tổng sinh viên</p>
                  <p className="mt-1 font-mm-mono text-base font-bold text-mm-heading">
                    {preview.total_students}
                  </p>
                </div>
                <div>
                  <p className="text-mm-text-muted">Đạt môn</p>
                  <p className="mt-1 font-mm-mono text-base font-bold text-emerald-700">
                    {preview.passed_count} ({preview.pass_rate_pct}%)
                  </p>
                </div>
                <div>
                  <p className="text-mm-text-muted">Rớt môn</p>
                  <p className="mt-1 font-mm-mono text-base font-bold text-rose-700">
                    {preview.failed_count} ({preview.fail_rate_pct}%)
                  </p>
                </div>
                <div>
                  <p className="text-mm-text-muted">Điểm TB</p>
                  <p className="mt-1 font-mm-mono text-base font-bold text-blue-700">
                    {preview.class_average_10 ?? "--"} / 10
                  </p>
                </div>
              </div>
            ) : null}

            {hasMutedColumns && preview && (
              <div className="rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-xs text-amber-900">
                <p className="font-semibold flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  Không thể khóa sổ điểm (E-GB-06)
                </p>
                <p className="mt-1">
                  Các cột điểm sau vẫn đang ở trạng thái ẩn (Muted):{" "}
                  <strong>{preview.muted_columns.join(", ")}</strong>. Vui lòng công bố toàn bộ điểm
                  trước khi khóa niêm phong.
                </p>
              </div>
            )}

            <div className="rounded-xl border border-rose-300 bg-rose-50 p-3.5 text-xs leading-relaxed text-rose-900">
              <strong>Lưu ý pháp lý:</strong> Sau khi khóa sổ điểm, toàn bộ điểm số sẽ chuyển sang
              trạng thái <strong>CHỈ ĐỌC (Read-Only)</strong> vĩnh viễn và được bảo vệ bởi Trigger
              CSDL. Mọi chỉnh sửa sau đó bắt buộc phải có quyết định phúc khảo chính thức.
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-mm-heading">
                Để xác nhận khóa, vui lòng gõ chính xác cụm từ:{" "}
                <strong className="font-mm-mono text-rose-700">KHOA DIEM</strong>
              </label>
              <input
                type="text"
                value={confirmPhrase}
                onChange={(e) => setConfirmPhrase(e.target.value)}
                placeholder="Gõ chính xác: KHOA DIEM"
                className="w-full rounded-xl border border-mm-border px-3 py-2 font-mm-mono text-sm focus:border-rose-500 focus:outline-none"
              />
              {confirmPhrase.length > 0 && !isExactPhrase && (
                <p className="text-xs text-rose-600">
                  Cụm từ nhập vào chưa khớp chính xác. Vui lòng gõ đúng chữ in hoa: KHOA DIEM (E-LOCK-01).
                </p>
              )}
            </div>

            <div className="flex justify-end gap-2 border-t border-mm-divider pt-4">
              <MmButton variant="secondary" onClick={onClose}>
                <span>Hủy</span>
              </MmButton>
              <MmButton
                variant="danger"
                disabled={!canConfirmLock}
                loading={submitting}
                onClick={handleConfirmLock}
              >
                <Lock className="h-4 w-4" />
                <span>Tôi Xác Nhận Khóa Sổ Điểm</span>
              </MmButton>
            </div>
          </div>
        ) : (
          <form onSubmit={handleConfirmUnlock} className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-mm-heading">
                Mã quyết định phúc khảo / Số công văn *
              </label>
              <input
                type="text"
                required
                value={decisionCode}
                onChange={(e) => setDecisionCode(e.target.value)}
                placeholder="VD: QD-2026-09/CNTT"
                className="w-full rounded-xl border border-mm-border px-3 py-2 font-mm-mono text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-mm-heading">
                Lý do điều chỉnh (tối thiểu 30 ký tự) *
              </label>
              <textarea
                rows={4}
                required
                value={unlockReason}
                onChange={(e) => setUnlockReason(e.target.value)}
                placeholder="Nêu rõ căn cứ quyết định phúc khảo của Ban Chủ nhiệm Khoa / Phòng Đào tạo..."
                className="w-full rounded-xl border border-mm-border px-3 py-2 text-sm"
              />
              <p className="mt-1 text-[11px] text-mm-text-muted">
                Độ dài hiện tại: {unlockReason.trim().length} / 30 ký tự tối thiểu
              </p>
            </div>
            <div className="flex justify-end gap-2 border-t border-mm-divider pt-4">
              <MmButton variant="secondary" type="button" onClick={onClose}>
                <span>Hủy</span>
              </MmButton>
              <MmButton variant="brand" type="submit" loading={submitting}>
                <Unlock className="h-4 w-4" />
                <span>Xác nhận Mở khóa & Lưu vết</span>
              </MmButton>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
